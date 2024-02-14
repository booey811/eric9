import logging
import time
from dateutil.parser import parse
import os
import datetime
from rq.job import Job
from typing import List
from pprint import pprint as p

import config
from ...services import monday
from ...services.motion import MotionClient, MotionRateLimitError, MotionError
from ...utilities import users, notify_admins_of_error
from ... import conf
from ...errors import EricError
from ...cache import get_redis_connection
from ...cache.rq import q_high

log = logging.getLogger('eric')


def schedule_update(repair_group_id):
	user = users.User(repair_group_id=repair_group_id)
	job_id = f"schedule_sync:{user.monday_id}"

	scheduled_registry = q_high.scheduled_job_registry

	# Check if there are any existing jobs for this task/user and cancel them
	for job_id in scheduled_registry.get_job_ids():
		job = Job(job_id, get_redis_connection())
		if job.meta.get('schedule_task_id') == job_id:
			scheduled_registry.remove(job)

	# Schedule a new job to update Monday.com after the delay period
	job = q_high.enqueue_in(
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
		statuses_to_ignore = ['Clamped', 'Battery Testing', 'Software Install']

		log.debug(f"Syncing for user: {user.name}")

		tech_group_ids = [api_data['id'] for api_data in monday.api.get_api_items_by_group(conf.MONDAY_MAIN_BOARD_ID, monday_group_id)]
		repair_group_ids = [api_data['id'] for api_data in monday.api.get_api_items_by_group(conf.MONDAY_MAIN_BOARD_ID, conf.UNDER_REPAIR_GROUP_ID)]

		tech_group_data = monday.api.get_api_items(tech_group_ids)
		tech_group_items = [monday.items.MainItem(data['id'], data) for data in tech_group_data]

		under_repair_data = monday.api.get_api_items(repair_group_ids)
		under_repair_group_items = [monday.items.MainItem(data['id'], data) for data in under_repair_data]

		assigned_repair_group_item = [
			r for r in under_repair_group_items
			if str(r.technician_id.value) == str(user.monday_id)
		]

		status_valid_under_repair_items = [r for r in assigned_repair_group_item if r.main_status not in statuses_to_ignore]

		repairs = tech_group_items + status_valid_under_repair_items

		log.debug(f"Syncing for repairs: {[repair.name for repair in repairs]}")

		clean_motion_tasks(user, repairs)
		add_monday_tasks_to_motion(user, repairs)

		log.info(f"Waiting 5 Seconds to allow Motion to complete scheduling")
		sync_monday_phase_deadlines(user, repairs)
	except MotionRateLimitError as e:
		log.error(f"Motion Rate Limit Error: {e}")
		schedule_update(monday_group_id)
	return True


def clean_motion_tasks(user, repairs: List[monday.items.MainItem]):
	# delete unassigned tasks in motion
	log.debug(f"Cleaning Motion of unassigned tasks: {user.name}; repairs={[_.name for _ in repairs]}")
	motion = MotionClient(user)
	schedule = motion.list_tasks()['tasks']
	monday_task_ids = [repair.motion_task_id.value for repair in repairs]
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
				repair = [repair for repair in repairs if repair.motion_task_id.value == task['id']][0]
				log.debug(f"Removing monday reference for Motion Task ID")
				repair.motion_task_id = ""
				repair.commit()
			except IndexError:
				# no task in group with this ID, so we don't care
				pass
		else:
			raise RuntimeError('Illogical result')

		if not task['scheduledEnd']:
			log.debug(f"Task {task['id']} has no scheduledEnd, deleting")
			while True:
				try:
					motion.delete_task(task['id'])
					break
				except MotionRateLimitError:
					log.debug("Waiting 20 seconds for rate limit")
					time.sleep(20)
			try:
				repair = [repair for repair in repairs if repair.motion_task_id.value == task['id']][0]
				log.debug(f"Removing monday reference for Motion Task ID")
				repair.motion_task_id = ""
				repair.commit()
			except IndexError:
				# no task in group with this ID, so we don't care
				pass


def add_monday_tasks_to_motion(user: users.User, repairs: List[monday.items.MainItem]):
	# add any tasks that are on monday, but not motion
	log.debug("Adding Monday tasks to Motion")

	motion = MotionClient(user)
	schedule = motion.list_tasks()['tasks']
	motion_task_ids = [t['id'] for t in schedule]
	for repair in repairs:
		log.debug(f'Checking {repair.name}({repair.id})')
		monday_task_id = repair.motion_task_id.value
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
			if not repair.hard_deadline.value:
				raise MissingDeadlineInMonday(repair)
			while True:
				try:
					if repair.products_connect.value:
						product_data = monday.api.get_api_items(repair.products_connect.value)
						products = [monday.items.ProductItem(p['id'], p) for p in product_data]
						duration = max([p.required_minutes.value for p in products])

						log.debug(f"Creating task with products, maximum duration={duration}")
						if not duration:
							log.debug("No duration found, using default duration")
							notify_admins_of_error(f"Repair {repair.name} has no duration, assuming 1 hour")
							duration = 60
					else:
						log.debug("No Products assigned, using default duration")
						notify_admins_of_error(f"Repair {repair.name} has no products, assuming 1 hour")
						duration = 60
					log.debug("Creating task....")
					task = motion.create_task(
						name=repair.name,
						deadline=repair.hard_deadline.value,
						description=repair.description.value,
						labels=['Repair'],
						duration=duration
					)
					break
				except MotionRateLimitError:
					log.debug("Waiting 20 seconds for rate limit")
					time.sleep(20)
		except MissingDeadlineInMonday:
			log.debug('Cannot plot task to Motion as no deadline has been provided')
			continue

		log.debug(f"Updating Monday Motion Task ID: {task['id']}")
		repair.motion_task_id = task['id']
		repair.commit()


def sync_monday_phase_deadlines(user, repairs: List[monday.items.MainItem]):
	"""
	gets motion tasks and syncs their scheduled deadlines with monday's phase deadlines
	assumes that the tasks have been cleaned in both directions
	uses monday as the source of truth and cycles through the repairs, searching for them in Motion
	"""

	log.debug(f"Syncing Monday Deadlines to Motion: {repairs}")

	motion_client = MotionClient(user)
	schedule = motion_client.list_tasks()['tasks']
	# now we actually schedule Monday
	for repair in repairs:
		try:
			log.debug(f"Syncing {repair} with Motion ID {repair.motion_task_id.value}")
			# cycle through Monday repairs, raising errors for incorrect values
			try:
				motion_task = [t for t in schedule if t['id'] == repair.motion_task_id.value][0]
			except IndexError:
				# this means we have Motion Task ID in Monday that does not exist in Motion, we should replace this value
				log.debug(f"Cannot find Motion task with ID: {repair.motion_task_id.value}")
				continue
			try:
				motion_deadline = parse(motion_task['scheduledEnd'])
			except TypeError:
				log.error(f"Received No Deadline from Motion Schedule for {str(repair)}, deleting")
				log.debug(motion_task)
				motion_client.delete_task(motion_task['id'])
				repair.motion_scheduling_status = "No Scheduled End"
				repair.motion_task_id = ""
				repair.commit()
				notify_admins_of_error(f"Motion Task {motion_task['id']} has no scheduledEnd\n\n{motion_task}")
				continue
			# raise MotionError(f"Motion Task {motion_task['id']} has no scheduledEnd")
			motion_deadline = motion_deadline.replace(microsecond=0, second=0).astimezone(datetime.timezone.utc)
			log.debug(f"Motion Deadline: {motion_deadline.strftime('%c')}")

			cs_deadline = repair.hard_deadline.value
			if not cs_deadline:
				raise MissingDeadlineInMonday(repair)
			cs_deadline = cs_deadline.replace()
			cs_deadline = cs_deadline.replace(microsecond=0, second=0).astimezone(datetime.timezone.utc)
			if cs_deadline < datetime.datetime.now(datetime.timezone.utc):
				raise DeadlineInPast(repair)

			log.debug(f"Monday Deadline: {cs_deadline.strftime('%c')}")

			# check is proposed Motion deadline is after Client side deadline
			if motion_deadline > cs_deadline:
				raise NotEnoughTime(repair)
			else:
				repair.phase_deadline = motion_deadline
				repair.motion_scheduling_status = "Synced"

		except MissingDeadlineInMonday:
			log.debug(f"Missing Deadline in Monday: {str(repair)}, removed from schedule")
			repair.phase_deadline = None
			repair.motion_task_id = ""
			motion_client.delete_task(repair.motion_task_id)

		except NotEnoughTime:
			log.debug(f"Not Enough Time in schedule to complete {str(repair)}")
			repair.phase_deadline = None

		except DeadlineInPast:
			log.debug(f"Deadline in Past for {str(repair)}, removed from schedule")
			repair.phase_deadline = None
			repair.motion_task_id = ""
			motion_client.delete_task(repair.motion_task_id)

		repair.commit()


class SchedulingError(EricError):

	def __init__(self, monday_item: monday.items.MainItem):
		self.item = monday_item
		monday_item.phase_deadline = None
		monday_item.commit()

	def __str__(self):
		return f"Scheduling Error: {str(self.item)}"


class MissingDeadlineInMonday(SchedulingError):

	def __init__(self, monday_item: monday.items.MainItem):
		monday_item.motion_scheduling_status = "No Deadline"
		monday_item.phase_deadline = None
		super().__init__(monday_item)

	def __str__(self):
		return f"No deadline on {str(self.item)}"


class NotEnoughTime(SchedulingError):
	def __init__(self, monday_item: monday.items.MainItem):
		monday_item.motion_scheduling_status = "Not Enough Time"
		monday_item.phase_deadline = None
		super().__init__(monday_item)

	def __str__(self):
		return f"Not Enough Time in schedule to complete {str(self.item)}"


class DeadlineInPast(SchedulingError):
	def __init__(self, monday_item: monday.items.MainItem):
		monday_item.motion_scheduling_status = "Deadline in Past"
		monday_item.phase_deadline = None
		super().__init__(monday_item)

	def __str__(self):
		return f"Deadline in Past for {str(self.item)}"
