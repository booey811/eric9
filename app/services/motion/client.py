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
		assignee_id: str,
		description: str = "",
		project_id=None,
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
		"assigneeId": assignee_id
	}
	if labels:
		payload['labels'] = labels
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


def update_task(task_id, deadline: datetime.datetime = None):
	url = f"https://api.usemotion.com/v1/tasks/{task_id}"

	payload = {
		"dueDate": deadline.isoformat(),
	}
	headers = {
		"Content-Type": "application/json",
		"Accept": "application/json",
		"X-API-Key": api_key
	}

	response = requests.patch(url, json=payload, headers=headers)
	if response.status_code == 200:
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


def list_tasks(assignee_id, label='Repair'):
	url = "https://api.usemotion.com/v1/tasks"

	querystring = {"assigneeId": assignee_id}
	if label:
		querystring["label"] = label

	headers = {
		"Accept": "application/json",
		"X-API-Key": api_key
	}

	response = requests.get(url, headers=headers, params=querystring)

	return response.json()


def delete_task(task_id):
	url = f"https://api.usemotion.com/v1/tasks/{task_id}"
	headers = {"X-API-Key": api_key}
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
