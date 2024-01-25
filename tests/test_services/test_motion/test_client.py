import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from app.services.motion.client import MotionClient, MotionError, MotionRateLimitError
from app.utilities import users


@pytest.fixture
def motion_user():
	user = Mock(spec=users.User)
	user.name = 'testuser'
	user.motion_api_token = 'test_api_token'
	user.motion_assignee_id = 'test_assignee_id'
	return user


@pytest.fixture
def motion_client(motion_user):
	with patch('app.services.motion.client.MotionClient.api_key', new_callable=Mock):
		client = MotionClient(motion_user)
		client.api_key = 'test_api_key'  # Mocked API Key
		yield client


@pytest.fixture
def mock_redis():
	with patch('app.services.motion.client.get_redis_connection') as mock_redis_conn:
		# Mock Redis client with a counter for the rate
		mock_redis = Mock()
		mock_redis.get.return_value = "0"
		mock_redis_conn.return_value = mock_redis
		yield mock_redis


@pytest.fixture
def mock_requests_200():
	with patch('app.services.motion.client.requests') as mock_req:
		mock_response = Mock()
		# Configure the mock to return a response with an OK status, etc.
		mock_response.status_code = 200
		mock_response.json.return_value = {"success": True}
		mock_req.get.return_value = mock_response
		mock_req.post.return_value = mock_response
		mock_req.patch.return_value = mock_response
		mock_req.delete.return_value = mock_response
		yield mock_req


@pytest.fixture
def mock_requests_201():
	with patch('app.services.motion.client.requests') as mock_req:
		mock_response = Mock()
		# Configure the mock to return a response with an OK status, etc.
		mock_response.status_code = 201
		mock_response.json.return_value = {"success": True}
		mock_req.get.return_value = mock_response
		mock_req.post.return_value = mock_response
		mock_req.patch.return_value = mock_response
		mock_req.delete.return_value = mock_response
		yield mock_req


def test_create_task_within_rate_limit(motion_client, mock_requests_201, mock_redis):
	"""Test creating a task without exceeding the rate limit"""
	deadline = datetime.now()
	labels = ['Test']
	name = 'Test Task'
	description = 'Test Description'
	duration = 60

	task = motion_client.create_task(name, deadline, description, duration, labels)
	assert task == {"success": True}
	mock_requests_201.post.assert_called_once()
	mock_redis.get.assert_called_once()
	# Ensure counter is incremented
	mock_redis.incr.assert_called_once()


def test_create_task_exceed_rate_limit(motion_client, mock_requests_200, mock_redis):
	"""Test creating a task when the rate limit is reached"""
	mock_redis.get.return_value = "12"

	with pytest.raises(MotionRateLimitError):
		task = motion_client.create_task("Test Task", datetime.now(), motion_client._user)


def test_update_task_within_rate_limit(motion_client, mock_requests_200, mock_redis):
	"""Test updating a task without exceeding the rate limit"""
	task_id = "task123"
	deadline = datetime.now()

	response = motion_client.update_task(task_id, deadline)
	assert response == {"success": True}
	mock_requests_200.patch.assert_called_once()
	mock_redis.get.assert_called_once()
	mock_redis.incr.assert_called_once()

# Similar test cases can be written for get_me, list_tasks, and delete_task methods
