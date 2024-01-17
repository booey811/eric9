import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timedelta
from app.tasks.scheduling import clean_motion_tasks, add_monday_tasks_to_motion, sync_monday_phase_deadlines
from app.models import MainModel
from app.utilities.users import User
from app import EricError

mock_list_tasks_return_missing_from_monday = {
	'tasks': [
		{'id': 'MISSINGTASK1'},
		{'id': 'MISSINGTASK2'},
		{'id': 'MISSINGTASK3'},
		{'id': 'MISSINGTASK4'},
		{'id': 'MISSINGTASK5'},
		# Add other tasks not present in `monday_task_ids`
	]
}

# Fixture for a mocked MotionClient
@pytest.fixture
def mock_motion_client():
	with patch('app.tasks.scheduling.MotionClient') as MockClient:
		# Mock instance of MotionClient
		mock_client = MockClient()
		mock_client.list_tasks.return_value = {'tasks': []}		# Setup for `mock_motion_client`
		yield mock_client


# Fixture for mocked MainModel instances
@pytest.fixture
def mock_repair_items():
	# Create a list of mocked MainModel instances
	mock_items = [Mock(spec=MainModel) for _ in range(5)]
	for i, item in enumerate(mock_items, start=1):
		item.id = i
		item.model.name = f"Repair {i}"
		item.model.motion_task_id = f"task_{i}"
	return mock_items


# Fixture for a mocked User with a repair_group_id
@pytest.fixture
def mock_user():
	mock_user = Mock(spec=User)
	mock_user.repair_group_id = 'group_id'
	mock_user.name = 'username'
	return mock_user


# Test the clean_motion_tasks function
def test_clean_motion_tasks(mock_user, mock_motion_client, mock_repair_items):
	with patch('app.tasks.scheduling.monday.get_group_items') as mock_get_group_items:
		# Mocking the response from get_group_items
		mock_get_group_items.return_value = mock_repair_items
		mock_motion_client.list_tasks.return_value = mock_list_tasks_return_missing_from_monday

		# Call the function we are testing
		clean_motion_tasks(mock_user, mock_repair_items)

		# Assert the delete_task was called the correct number of times
		assert mock_motion_client.delete_task.call_count == len(mock_repair_items)


# Test the add_monday_tasks_to_motion function
def test_add_monday_tasks_to_motion(mock_user, mock_motion_client, mock_repair_items):
	with patch('app.tasks.scheduling.monday.get_group_items') as mock_get_group_items:
		mock_get_group_items.return_value = mock_repair_items

		# Assume the repair items are not in the MotionClient's returned tasks
		add_monday_tasks_to_motion(mock_user, mock_repair_items)

		# Assert create_task is called for each repair item
		assert mock_motion_client.create_task.call_count == len(mock_repair_items)


# Test the sync_monday_phase_deadlines function
def test_sync_monday_phase_deadlines(mock_user, mock_motion_client, mock_repair_items):
	with patch('app.tasks.scheduling.monday.get_group_items') as mock_get_group_items:
		mock_get_group_items.return_value = mock_repair_items

		# Create a deadline a minute from now
		deadline = datetime.now() + timedelta(minutes=1)
		for item in mock_repair_items:
			item.model.hard_deadline = deadline

		mock_list_tasks_return = {
			'tasks': [
				{'id': 'task_1'},
				{'id': 'task_2'},
				{'id': 'task_3'},
				{'id': 'task_4'},
				{'id': 'task_5'},
				# Add other tasks not present in `monday_task_ids`
			]
		}

		mock_motion_client.list_tasks.return_value = mock_list_tasks_return

		# Call the function we are testing
		sync_monday_phase_deadlines(mock_user, mock_repair_items)

		# Assert the deadline is updated for each repair item
		for item in mock_repair_items:
			item.model.save.assert_called_once_with()
			assert item.model.phase_deadline == deadline