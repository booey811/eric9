import os
import functools

import requests
import datetime

from ... import EricError
from ...cache import get_redis_connection
from ...utilities import users

WORKSPACE_IDS = {
	"test": "YtAs_s8Ec0orh6ck5qc2T"
}


class RateLimiter:
	def __init__(self, name, max_calls, period):
		self.redis = get_redis_connection()
		self.key = f"rate_limit:{name}"
		self.max_calls = max_calls
		self.period = period

	def is_rate_limited(self):
		count = self.redis.get(self.key)
		print(count)
		if not count:
			# If the key does not exist, no calls have been made in the period
			self.redis.setex(self.key, self.period, 1)
			return False
		elif int(count) < self.max_calls:
			# If the number of calls made is less than the maximum, increment the counter
			self.redis.incr(self.key)
			return False
		return True  # The limit has been reached


rate_limiters = {}


def rate_limit_decorator(func):
	"""Decorator that checks rate limits before executing the function."""

	@functools.wraps(func)
	def wrapper(*args, **kwargs):
		user = kwargs.get('user')

		# Retrieve the corresponding RateLimiter for the given API token,
		# or initialize one if it's the first time we're seeing this token.
		if user.motion_api_key not in rate_limiters:
			# Note: You'll need to determine the right max_calls and period for your case.
			rate_limiters[user.motion_api_key] = RateLimiter(user.motion_api_key, max_calls=12, period=60)

		rate_limiter = rate_limiters[user.motion_api_key]
		if rate_limiter.is_rate_limited():
			raise MotionRateLimitError(user.name)

		return func(*args, **kwargs)

	return wrapper


@rate_limit_decorator
def create_task(
		name,
		deadline: datetime.datetime,
		user: users.User,
		description: str = "",
		duration=60,
		labels=['Repair']
):
	url = "https://api.usemotion.com/v1/tasks"

	payload = {
		"dueDate": deadline.isoformat(),
		"duration": duration,
		"status": "auto-scheduled",
		"autoScheduled": {
			"startDate": datetime.datetime.now().isoformat(),
			"deadlineType": "HARD",
			"schedule": "Work Hours"
		},
		"name": name,
		"projectId": "",
		"workspaceId": "lrZBuj9OLURaRVGRfe-kM",
		"description": description,
		"priority": "MEDIUM",
		"assigneeId": user.motion_assignee_id
	}
	if labels:
		payload['labels'] = labels
	headers = {
		"Content-Type": "application/json",
		"Accept": "application/json",
		"X-API-Key": user.motion_api_key
	}

	response = requests.post(url, json=payload, headers=headers)
	if response.status_code == 201:
		return response.json()
	else:
		raise MotionError(response.text)


@rate_limit_decorator
def update_task(task_id, user: users.User, deadline: datetime.datetime = None):
	url = f"https://api.usemotion.com/v1/tasks/{task_id}"

	payload = {
		"dueDate": deadline.isoformat(),
	}
	headers = {
		"Content-Type": "application/json",
		"Accept": "application/json",
		"X-API-Key": user.motion_api_key
	}

	response = requests.patch(url, json=payload, headers=headers)
	if response.status_code in (200, 201):
		return response.json()
	else:
		raise MotionError(response.text)


@rate_limit_decorator
def get_users(user: users.User):
	url = "https://api.usemotion.com/v1/users"
	headers = {
		"Accept": "application/json",
		"X-API-Key": user.motion_api_key
	}

	response = requests.get(url, headers=headers)

	return response.json()


@rate_limit_decorator
def get_me(user: users.User):
	url = "https://api.usemotion.com/v1/users/me"

	headers = {
		"Accept": "application/json",
		"X-API-Key": user.motion_api_key
	}

	response = requests.get(url, headers=headers)

	return response.json()


@rate_limit_decorator
def list_tasks(user, label='Repair'):
	url = "https://api.usemotion.com/v1/tasks"

	querystring = {"assigneeId": user.motion_assignee_id}
	if label:
		querystring["label"] = label

	headers = {
		"Accept": "application/json",
		"X-API-Key": user.motion_api_key
	}

	response = requests.get(url, headers=headers, params=querystring)

	return response.json()


@rate_limit_decorator
def delete_task(task_id, user: users.User):
	url = f"https://api.usemotion.com/v1/tasks/{task_id}"
	headers = {"X-API-Key": user.motion_api_key}
	response = requests.delete(url, headers=headers)
	if response.status_code == 204:
		return True
	else:
		raise MotionError(f"Could Not Delete Motion Task: {response.text}")


class MotionError(EricError):

	def __init__(self, message=""):
		self.message = message

	def __str__(self):
		return f"MotionAPI Error: {self.message}"


class MotionRateLimitError(MotionError):

	def __init__(self, user_name):
		self.name = user_name

	def __str__(self):
		return f"Motion Rate Limit Reached. API call stopped to prevent ban"
