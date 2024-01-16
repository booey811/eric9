import logging
import time
from dateutil.parser import parse

from ...services import monday
from ...services import slack
from ...models import MainModel
from ...services.motion import create_task, update_task, list_tasks, delete_task, MotionError
from ...utilities import users

log = logging.getLogger('eric')


def sync_schedule(user: users.User):
	"""this will sync motion's current schedule with Monday, and post to slack"""
	# get motion schedule
	schedule = list_tasks(user=user)
	edited = False
	slack_blocks = []


	repair_group_items = monday.get_group_items(349212843, user.repair_group_id)
	repairs = [MainModel(item) for item in repair_group_items]

	plotted_task_ids = [repair.model.motion_task_id for repair in repairs]
	for task in schedule:
		if task['id'] not in plotted_task_ids:
			log.debug(f"Found errant task: {task['id']}")
			delete_task(task['id'], user)
			edited = True

	if edited:
		seconds = 5
		log.debug(f"Schedule edited: Waiting for Motion to reschedule {seconds} and re-fetching")
		time.sleep(seconds)
		schedule = list_tasks(user=user)

	# now we actually schedule Monday
	for task in schedule:
		repair = [repair for repair in repairs if repair.model.motion_task_id == task['id']][0]
		repair.model.phase_deadline = parse(task['scheduledEnd'])
		repair.model.save()
		slack_blocks.append(slack.blocks.add.text_block(f"{repair.model.name}"))
		slack_blocks.append(slack.blocks.add.text_block(f"{task['scheduledStart']} -> {task['scheduledEnd']}"))





def sync_monday_with_motion(group_id="new_group26478"):
	main_board = monday.client.get_board(349212843)
	group = main_board.get_group(id=group_id)
	items = monday.get_items([item.id for item in group.items], column_values=True)
	models = [MainModel(item.id, item) for item in items]
	for model in models:
		if model.model.motion_task_id:
			update_task(model.model.motion_task_id, model.model.hard_deadline)
		else:
			task = create_task(
				name=model.model.name,
				deadline=model.model.hard_deadline,
				description=model.model.requested_repairs,
			)
			model.model.motion_task_id = task['id']
			model.model.save()

	tasks = list_tasks(label='Repair')['tasks']
	for task in tasks:
		phase_deadline = parse(task['scheduledEnd'])
		for model in models:
			if str(model.model.motion_task_id) == str(task['id']):
				if model.model.hard_deadline < phase_deadline:
					model.model.motion_scheduling_status = 'Error'
				model.model.phase_deadline = phase_deadline
				model.model.save()
				break
