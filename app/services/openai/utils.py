import datetime
import os
import time
import requests

from openai import OpenAI

from ... import get_config, EricError
from ...cache import rq

SLACK_AI_CHANNELS = {
	"production": "C067N48R6NB",
	"development": "C065KT7B4TX"
}

ASSISTANT_IDS = (
	('enquiry_assistant', "asst_RLYPxU9Qdkpj4btu0bLQbJ1s"),
	('beta_enquiry_assistant', "asst_eVXTDPB8214CmYosU512OKPo")
)

conf = get_config()

client = OpenAI(api_key=conf.OPENAI_KEY)

ai_results = rq.queues['ai_results']


def check_run(thread_id, run_id, success_endpoint=''):
	run = fetch_run(thread_id, run_id)
	try:
		if run.status == 'completed':
			# post to success endpoint
			data = run.metadata

			requests.post(success_endpoint, json=data)

		elif run.status in ('in_progress', 'queued'):
			# job still being completed, requeue
			ai_results.enqueue_in(
				time_delta=datetime.timedelta(seconds=5),
				func=check_run,
				kwargs={
					"thread_id": thread_id,
					"run_id": run.id,
					"success_endpoint": success_endpoint,
				}
			)
			return run
		else:
			raise InvalidRunStatus(run_id, thread_id, run.status)

	except Exception as e:
		raise e


def get_assistant_data(id_or_name):
	for pair in ASSISTANT_IDS:
		if id_or_name in pair:
			return {
				'name': pair[0],
				'id': pair[1]
			}
	raise KeyError(f"No Assistant with ID or Name '{id_or_name}'")


def create_and_run_thread(assistant_id: str = None, endpoint: str = None, kwargs: dict = None, messages: list = None):
	metadata = {}

	if endpoint:
		metadata['endpoint'] = endpoint

	for kwarg in kwargs:
		metadata[kwarg] = kwargs[kwarg]

	run = client.beta.threads.create_and_run(
		assistant_id=assistant_id,
		thread={
			"messages": messages
		},
		metadata=metadata
	)

	return run


def create_thread(metadata: dict = None):
	if metadata is None:
		metadata = {}

	if metadata:
		empty_thread = client.beta.threads.create(metadata=metadata)
	else:
		empty_thread = client.beta.threads.create()
	return empty_thread


def fetch_thread(thread_id):
	thread = client.beta.threads.retrieve(thread_id=thread_id)
	return thread


def add_message_to_thread(thread_id, message, metadata={}):
	message_obj = client.beta.threads.messages.create(
		thread_id=str(thread_id),
		role="user",
		content=message,
		metadata=metadata
	)
	return message_obj


def run_thread(thread_id, assistant_id):
	run_obj = client.beta.threads.runs.create(
		thread_id=thread_id,
		assistant_id=assistant_id
	)
	return run_obj


def fetch_run(thread_id, run_id):
	run_obj = client.beta.threads.runs.retrieve(
		thread_id=thread_id,
		run_id=run_id
	)
	return run_obj


def list_messages(thread_id, limit=20):
	result = client.beta.threads.messages.list(thread_id, limit=limit)
	return result


class InvalidRunStatus(EricError):

	def __init__(self, run_id, thread_id, status):
		self.run_id = run_id
		self.thread_id = thread_id
		self.status = status

	def __str__(self):
		return f"Run {self.run_id} in Thread {self.thread_id} has invalid status: {self.status}"