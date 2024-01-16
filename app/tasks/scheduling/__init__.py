import time
from dateutil.parser import parse

from ...services import monday
from ...models import MainModel
from ...services.motion import create_task, update_task, list_tasks


def sync_schedule(user_info):
	pass

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
