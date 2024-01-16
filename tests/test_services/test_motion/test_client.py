import pytest
from unittest.mock import Mock, patch
import datetime
from app.services.motion.client import create_task, RateLimiter, update_task, get_users, get_me, list_tasks, delete_task


# Mock the users.User object
@pytest.fixture
def mock_user():
	mock_user = Mock()
	mock_user.motion_api_token = "mock_api_token"
	mock_user.motion_api_key = "mock_api_key"
	mock_user.motion_assignee_id = "mock_assignee_id"
	mock_user.name = "Mock User"
	return mock_user


# Fixture to mock Redis connection
@pytest.fixture
def mock_redis():
	with patch('app.services.motion.client.get_redis_connection') as mock_redis_conn:
		mock_redis = Mock()
		mock_redis.get.return_value = None  # Simulate no rate limiting count
		mock_redis.setex.return_value = None
		mock_redis.incr.return_value = None
		mock_redis_conn.return_value = mock_redis
		yield mock_redis


# Fixture to mock requests
@pytest.fixture
def mock_requests():
	with patch('app.services.motion.client.requests') as mock_requests:
		mock_response = Mock()
		mock_response.json.return_value = {"id": "123", "success": True}
		mock_response.status_code = 201
		mock_requests.post.return_value = mock_response
		mock_requests.patch.return_value = mock_response
		mock_requests.get.return_value = mock_response
		mock_requests.delete.return_value = mock_response
		yield mock_requests


# Test create_task with a successful response
def test_create_task(mock_user, mock_requests, mock_redis):
	deadline = datetime.datetime.now() + datetime.timedelta(days=1)
	response = create_task(name="New Task", deadline=deadline, user=mock_user)
	assert response.get("success") == True


# Test update_task with a successful response
def test_update_task(mock_user, mock_requests, mock_redis):
	deadline = datetime.datetime.now() + datetime.timedelta(days=1)
	response = update_task(task_id="mock_task_id", user=mock_user, deadline=deadline)
	assert response.get("success") == True


# Test get_users with a successful response
def test_get_users(mock_user, mock_requests, mock_redis):
	response = get_users(user=mock_user)
	assert isinstance(response, dict)


# Test get_me with a successful response
def test_get_me(mock_user, mock_requests, mock_redis):
	response = get_me(user=mock_user)
	assert isinstance(response, dict)


# Test list_tasks with a successful response
def test_list_tasks(mock_user, mock_requests, mock_redis):
	response = list_tasks(user=mock_user, label="Repair")
	assert isinstance(response, dict)


# Test delete_task with a successful response
def test_delete_task(mock_user, mock_requests, mock_redis):
	mock_requests.delete.return_value.status_code = 204  # Simulate successful delete
	result = delete_task(task_id="mock_task_id", user=mock_user)
	assert result == True


# Test RateLimiter directly
def test_rate_limiter(mock_redis):
	rate_limiter = RateLimiter("test_api_token", max_calls=12, period=60)
	assert not rate_limiter.is_rate_limited()


def test_rate_limit_reached(mock_redis):
	mock_redis.get.return_value = 12
	rate_limiter = RateLimiter("test_api_token", max_calls=12, period=60)
	assert rate_limiter.is_rate_limited() is True
