import datetime

from ...models import MainModel
from .client import MotionError, MotionClient
from ...utilities import users
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
