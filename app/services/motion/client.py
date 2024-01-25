import logging
import os
import functools

import requests
import datetime

from ... import EricError, conf
from ...cache import get_redis_connection
from ...utilities import users

log = logging.getLogger('eric')

WORKSPACE_IDS = {
	"test": "YtAs_s8Ec0orh6ck5qc2T"
}


class MotionClient:
	"""basic interaction with the Motion API"""

	def __init__(self, user: users.User):
		self._user = user
		self._api_key = None

	@property
	def api_key(self):
		if self._api_key is None:
			self._api_key = conf.MOTION_KEYS.get(self._user.name)
			if not self._api_key:
				raise EnvironmentError(f"No env variable: MOTION_{self._user.name.upper()}")
		return self._api_key

	def rate_limit(self):
		"""checks if this user has hit their rate limit"""
		key = f"motion_rate:{self._user.name}"
		max_calls = 12
		duration = 60
		log.debug(f"Checking rate limit with key: {key}, max_calls: {max_calls}, duration={duration}")

		count = get_redis_connection().get(key)
		log.debug(f"Got {count}")
		if not count:
			# If the key does not exist, no calls have been made in the period
			log.debug(f'MISS: setting {key}, {duration} seconds, 1 counts')
			get_redis_connection().setex(key, duration, 1)
			return 0
		elif int(count) < max_calls:
			# If the number of calls made is less than the maximum, increment the counter
			count = int(count) + 1
			log.debug(f'Limit not reached, count increased to {count}')
			get_redis_connection().incr(key)
			return count
		log.error(f"Motion Rate limit hit: {self._user.name}")
		raise MotionRateLimitError(self._user.name)

	def create_task(
			self,
			name: str,
			deadline: datetime.datetime,
			description: str = "",
			duration: int = 60,
			labels: list = ()
	):
		url = "https://api.usemotion.com/v1/tasks"

		payload = {
			"dueDate": deadline.isoformat(),
			"duration": duration,
			"status": "",
			"autoScheduled": {
				"startDate": datetime.datetime.now().isoformat(),
				"deadlineType": "HARD",
				"schedule": "Work Hours"
			},
			"name": name,
			"projectId": "",
			"workspaceId": conf.TEAM_WORKSPACE_ID,
			"description": description,
			"priority": "MEDIUM",
			"assigneeId": self._user.motion_assignee_id
		}
		if labels:
			payload['labels'] = labels
		headers = {
			"Content-Type": "application/json",
			"Accept": "application/json",
			"X-API-Key": self.api_key
		}

		self.rate_limit()

		response = requests.post(url, json=payload, headers=headers)
		if response.status_code == 201:
			return response.json()
		else:
			raise MotionError(f"Could Not Create Motion Task ({response.status_code}): {response.text}")

	def update_task(self, task_id, deadline: datetime.datetime = None):
		url = f"https://api.usemotion.com/v1/tasks/{task_id}"

		payload = {
			"dueDate": deadline.isoformat(),
		}
		headers = {
			"Content-Type": "application/json",
			"Accept": "application/json",
			"X-API-Key": self.api_key
		}

		self.rate_limit()

		response = requests.patch(url, json=payload, headers=headers)
		if response.status_code in (200, 201):
			return response.json()
		else:
			raise MotionError(f"Could Not Update Motion Task ({response.status_code}): {response.text}")

	def get_me(self):
		url = "https://api.usemotion.com/v1/users/me"

		headers = {
			"Accept": "application/json",
			"X-API-Key": self.api_key
		}

		self.rate_limit()
		response = requests.get(url, headers=headers)

		return response.json()

	def list_tasks(self, label=''):
		url = "https://api.usemotion.com/v1/tasks"

		querystring = {"assigneeId": self._user.motion_assignee_id}
		if label:
			querystring["label"] = label

		headers = {
			"Accept": "application/json",
			"X-API-Key": self.api_key
		}
		self.rate_limit()
		response = requests.get(url, headers=headers, params=querystring)

		return response.json()

	def delete_task(self, task_id):
		log.debug(f"Deleting task {task_id}")
		url = f"https://api.usemotion.com/v1/tasks/{task_id}"
		headers = {"X-API-Key": self.api_key}
		self.rate_limit()
		response = requests.delete(url, headers=headers)
		if response.status_code == 204:
			log.debug(f"Deleted task {task_id}")
			return True
		elif response.status_code == 404:
			log.debug(f"Task {task_id} not found")
			return False
		else:
			raise MotionError(f"Could Not Delete Motion Task ({response.status_code}): {response.text}")


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
