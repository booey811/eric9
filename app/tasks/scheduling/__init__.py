import logging
import time
from dateutil.parser import parse
import os
import datetime

import config
from ...services import monday
from ...services import slack
from ...models import MainModel
from ...services.motion import MotionClient, MotionRateLimitError
from ...utilities import users
from ... import EricError

log = logging.getLogger('eric')
conf = config.get_config()


def clean_motion_tasks(user, repairs=[]):
	# delete unassigned tasks in motion
	log.debug(f"Cleaning Motion of unassigned tasks: {user.name}; repairs={[_.model.name for _ in repairs]}")
	motion = MotionClient(user)
	if not repairs:
		repair_group_items = monday.get_group_items(conf.MONDAY_MAIN_BOARD_ID, user.repair_group_id)
		repairs = [MainModel(item.id, item) for item in repair_group_items]
	schedule = motion.list_tasks()['tasks']
	monday_task_ids = [repair.model.motion_task_id for repair in repairs]
	log.debug(f"Task IDs from Monday: {monday_task_ids}")
	for task in schedule:
		log.debug(f"Checking Motion Task {task['id']}")
		if task['id'] in monday_task_ids:
			log.debug(f"Motion task exists in Monday repairs")
		elif task['id'] not in monday_task_ids:
			log.debug(f"Found errant task, deleting")
			while True:
				try:
					motion.delete_task(task['id'])
					break
				except MotionRateLimitError:
					log.debug("Waiting 20 seconds for rate limit")
					time.sleep(20)
			try:
				repair = [repair for repair in repairs if repair.model.motion_task_id == task['id']][0]
				log.debug(f"Removing monday reference for Motion Task ID")
				repair.model.motion_task_id = ""
				repair.model.save()
			except IndexError:
				# no task in group with this ID, so we don't care
				pass
		else:
			raise RuntimeError('Illogical result')


def add_monday_tasks_to_motion(user: users.User, repairs=[]):
	# add any tasks that are on monday, but not motion
	log.debug("Adding Monday tasks to Motion")

	if not repairs:
		repair_group_items = monday.get_group_items(conf.MONDAY_MAIN_BOARD_ID, user.repair_group_id)
		repairs = [MainModel(item.id, item) for item in repair_group_items]

	motion = MotionClient(user)
	schedule = motion.list_tasks()['tasks']
	motion_task_ids = [t['id'] for t in schedule]
	for repair in repairs:
		log.debug(f'Checking {repair.model.name}({repair.id})')
		monday_task_id = repair.model.motion_task_id
		log.debug(f'Motion Task ID: {monday_task_id}')
		if monday_task_id in motion_task_ids:
			log.debug(f"Task already plotted in Motion, skipping")
			continue
		log.debug("Attempting to add Task to Motion")
		if monday_task_id is None:
			# task needs to be added to motion
			log.debug("No Monday Task ID")
		elif monday_task_id not in motion_task_ids:
			log.debug(f"Monday Task ID {monday_task_id} not in Motion, creating and reassigning monday reference")
		else:
			raise RuntimeError("Impossible")
		while True:
			try:
				log.debug("Creating task....")
				task = motion.create_task(
					name=repair.model.name,
					deadline=repair.model.hard_deadline,
					description=repair.model.requested_repairs,
					labels=['Repair']
				)
				break
			except MotionRateLimitError:
				log.debug("Waiting 20 seconds for rate limit")
				time.sleep(20)

		log.debug(f"Updating Monday Motion Task ID: {task['id']}")
		repair.model.motion_task_id = task['id']
		repair.model.save()


def sync_monday_phase_deadlines(user, repairs=[]):
	"""
	gets motion tasks and syncs their scheduled deadlines with monday's phase deadlines
	assumes that the tasks have been cleaned in both directions
	uses monday as the source of truth and cycles through the repairs, searching for them in Motion
	"""
	if not repairs:
		repair_group_items = monday.get_group_items(conf.MONDAY_MAIN_BOARD_ID, user.repair_group_id)
		repairs = [MainModel(item.id, item) for item in repair_group_items]

	log.debug(f"Syncing Monday Deadlines to Motion: {repairs}")

	schedule = MotionClient(user).list_tasks()['tasks']
	# now we actually schedule Monday
	for repair in repairs:
		try:
			log.debug(f"Syncing {repair} with Motion ID {repair.model.motion_task_id}")
			# cycle through Monday repairs, raising errors for incorrect values
			try:
				motion_task = [t for t in schedule if t['id'] == repair.model.motion_task_id][0]
			except IndexError:
				log.debug(f"Cannot find Motion task with ID: {repair.model.motion_task_id}")
				raise SchedulingError(repair)

			start = parse(motion_task['scheduledStart'])
			motion_deadline = parse(motion_task['scheduledEnd'])
			motion_deadline.replace(microsecond=0, second=0)
			log.debug(f"Motion Deadline: {motion_deadline.strftime('%c')}")

			cs_deadline = repair.model.hard_deadline
			if not cs_deadline:
				raise MissingDeadlineInMonday(repair)
			cs_deadline.replace(microsecond=0, second=0)
			log.debug(f"Monday Deadline: {cs_deadline.strftime('%c')}")

			# check is proposed Motion deadline is after Client side deadline
			if motion_deadline > repair.model.hard_deadline:
				raise NotEnoughTime(repair)
			else:
				repair.model.phase_deadline = motion_deadline
				repair.model.motion_scheduling_status = "Synced"

		except MissingDeadlineInMonday:
			log.debug(f"Missing Deadline in Monday: {repair.model.name}")
			repair.model.phase_deadline = None

		except NotEnoughTime:
			log.debug(f"Not Enough Time in schedule to complete {repair.model.name}")
			repair.model.phase_deadline = None

		repair.model.save()


class SchedulingError(EricError):

	def __init__(self, monday_item: MainModel):
		self.item = monday_item
		monday_item.model.save()

	def __str__(self):
		return f"Scheduling Error: {self.item.model.name}"


class MissingDeadlineInMonday(SchedulingError):

	def __init__(self, monday_item: MainModel):
		monday_item.model.motion_scheduling_status = "No Deadline"
		super().__init__(monday_item)

	def __str__(self):
		return f"No deadline on {self.item.model.name}"


class NotEnoughTime(SchedulingError):
	def __init__(self, monday_item: MainModel):
		monday_item.model.motion_scheduling_status = "Not Enough Time"
		super().__init__(monday_item)

	def __str__(self):
		return f"Not Enough Time in schedule to complete {self.item.model.name}"