import logging
import time
from dateutil.parser import parse
import os
import datetime
from rq.job import Job

import config
from ...services import monday
from ...models import MainModel
from ...services.motion import MotionClient, MotionRateLimitError, MotionError
from ...utilities import users
from ... import EricError, conf
from app.cache import rq, get_redis_connection

log = logging.getLogger('eric')

def schedule_update(repair_group_id):
	user = users.User(repair_group_id=repair_group_id)
	job_id = f"schedule_sync:{user.monday_id}"

	scheduled_registry = rq.queues['high'].scheduled_job_registry

	# Check if there are any existing jobs for this task/user and cancel them
	for job_id in scheduled_registry.get_job_ids():
		job = Job(job_id, get_redis_connection())
		if job.meta.get('schedule_task_id') == job_id:
			scheduled_registry.remove(job)

	# Schedule a new job to update Monday.com after the delay period
	job = rq.queues['high'].enqueue_in(
		time_delta=datetime.timedelta(seconds=10),
		func=sync_repair_schedule,
		args=(user.repair_group_id,)
	)
	job.meta['schedule_task_id'] = job_id
	job.save_meta()


def sync_repair_schedule(monday_group_id):
	log.debug("Schedule Sync Requested")
	user = users.User(repair_group_id=monday_group_id)

	try:
		log.debug(f"Syncing for user: {user.name}")
		repairs = [MainModel(_.id, _) for _ in monday.get_group_items(conf.MONDAY_MAIN_BOARD_ID, monday_group_id)]
		log.debug(f"Syncing for repairs: {[repair.model.name for repair in repairs]}")

		clean_motion_tasks(user, repairs)
		add_monday_tasks_to_motion(user, repairs)

		log.info(f"Waiting 5 Seconds to allow Motion to complete scheduling")
		sync_monday_phase_deadlines(user, repairs)
	except MotionRateLimitError as e:
		log.error(f"Motion Rate Limit Error: {e}")
		schedule_update(monday_group_id)
	return True

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
		try:
			if not repair.model.hard_deadline:
				raise MissingDeadlineInMonday(repair)
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
		except MissingDeadlineInMonday:
			log.debug('Cannot plot task to Motion as no deadline has been provided')
			continue

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
				# this means we have Motion Task ID in Monday that does not exist in Motion, we should replace this value
				log.debug(f"Cannot find Motion task with ID: {repair.model.motion_task_id}")
				continue
			try:
				motion_deadline = parse(motion_task['scheduledEnd'])
			except TypeError:
				log.error(f"Received No Deadline from Motion Schedule for {repair.model.name}")
				repair.model.motion_scheduling_status = "Need More Time"
				repair.model.save()
				schedule_update(user.repair_group_id)
				raise MotionError(f"Motion Task {motion_task['id']} has no scheduledEnd")
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
		monday_item.model.phase_deadline = None
		monday_item.model.save()

	def __str__(self):
		return f"Scheduling Error: {self.item.model.name}"


class MissingDeadlineInMonday(SchedulingError):

	def __init__(self, monday_item: MainModel):
		monday_item.model.motion_scheduling_status = "No Deadline"
		monday_item.model.phase_deadline = None
		super().__init__(monday_item)

	def __str__(self):
		return f"No deadline on {self.item.model.name}"


class NotEnoughTime(SchedulingError):
	def __init__(self, monday_item: MainModel):
		monday_item.model.motion_scheduling_status = "Not Enough Time"
		monday_item.model.phase_deadline = None
		super().__init__(monday_item)

	def __str__(self):
		return f"Not Enough Time in schedule to complete {self.item.model.name}"
