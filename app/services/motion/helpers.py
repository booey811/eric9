import datetime
import time
from pprint import pprint as p

from dateutil.parser import parse

from ...models import MainModel
from .client import MotionError, create_task, update_task, list_tasks
from .. import monday

SAMPLE_TIME_STRINGS = ['2024-01-09T13:00:00.000Z', '2024-01-09T11:00:00.000Z', '2024-01-09T10:00:00.000Z',
					   '2024-01-09T09:00:00.000Z', '2024-01-09T12:00:00.000Z', '2024-01-11T12:00:00.000Z',
					   '2024-01-10T12:00:00.000Z', '2024-01-17T12:00:00.000Z']


def update_monday_deadline(main_item: MainModel, desired_deadline: datetime.datetime):
	try:
		main_item.model.phase_deadline = desired_deadline
	except Exception as e:
		raise MotionError(f"Error while updating Monday Deadline: {str(e)}")
	try:
		main_item.model.save()
	except Exception as e:
		raise MotionError(f"Error while saving Monday Item: {str(e)}")
	return main_item


def plot_monday_group_to_motion(monday_group_id="new_group49546"):
	main_board = monday.client.get_board(349212843)
	group = main_board.get_group(id=monday_group_id)
	items = monday.get_items([item.id for item in group.items], column_values=True)
	results = []
	for item in items:
		m = MainModel(item.id, item)
		if m.model.motion_task_id:
			# task already plotted, skipping
			continue
		print(f"Got {m.model.name}")
		try:
			deadline = m.model.hard_deadline.isoformat()
		except AttributeError:
			deadline = None
		print(f"Deadline: {deadline}")
		r = create_task(
			name=m.model.name,
			deadline=deadline,
			description=m.model.description
		)
		results.append(r)
		m.model.motion_task_id = r['id']
		m.model.save()
	return results

