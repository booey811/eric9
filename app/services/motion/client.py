import os

import requests
import datetime

from ... import EricError

api_key = os.environ["MOTION"]

WORKSPACE_IDS = {
	"test": "YtAs_s8Ec0orh6ck5qc2T"
}


def create_task(
		name,
		deadline: datetime.datetime,
		description: str = "",
		project_id=None,
		assignee_id: str = "vpCL0oYJ2Ocm6WrWXAS1AZXlrPw2",
		duration=60
):

	url = "https://api.usemotion.com/v1/tasks"

	payload = {
		"dueDate": deadline,
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
		"assigneeId": assignee_id
	}
	headers = {
		"Content-Type": "application/json",
		"Accept": "application/json",
		"X-API-Key": api_key
	}

	response = requests.post(url, json=payload, headers=headers)
	if response.status_code == 201:
		return response.json()
	else:
		raise MotionError(response.text)


def get_users():
	url = "https://api.usemotion.com/v1/users"
	headers = {
		"Accept": "application/json",
		"X-API-Key": api_key
	}

	response = requests.get(url, headers=headers)

	return response.json()


def get_me():
	url = "https://api.usemotion.com/v1/users/me"

	headers = {
		"Accept": "application/json",
		"X-API-Key": api_key
	}

	response = requests.get(url, headers=headers)

	return response.json()



def list_tasks(assignee_id=""):

	url = "https://api.usemotion.com/v1/tasks"

	querystring = {"assigneeId": "vpCL0oYJ2Ocm6WrWXAS1AZXlrPw2"}

	headers = {
		"Accept": "application/json",
		"X-API-Key": api_key
	}

	response = requests.get(url, headers=headers, params=querystring)

	return response.json()


class MotionError(EricError):

	def __init__(self, message=""):
		self.message = message

	def __str__(self):
		return f"MotionAPI Error: {self.message}"
