import datetime
import os
import time
from pprint import pprint as p

from ...services.slack import slack_app
from ...services import monday, openai
from ...tasks import slack as slack_tasks
from ...utilities import users

import config

conf = config.get_config()


@slack_app.event("message")
def handle_new_ai_thread_message(client, event, say):
	# List of desired channels
	desired_channels = list(conf.AI_CHANNEL_IDS.values())

	# Check if the event is from one of the desired channels and is not a threaded reply
	if event['channel'] in desired_channels and 'thread_ts' not in event and event['user'] != conf.SLACK_BOT:
		# Create a new thread in OpenAI's API
		output_message = say("Creating a new Assistant Thread for this message...", thread_ts=event['ts'])
		thread = openai.utils.create_thread()
		thread_id = thread.id
		output_message = slack_app.client.chat_update(
			text=f"Thread created with ID: {thread_id}.... saving to database...",
			channel=event['channel'],
			ts=output_message['ts'],
		).data

		user = users.User(slack_id=event['user'])
		blank_thread_store = monday.items.ai_threads.InvoiceAssistantThreadItem()
		blank_thread_store.thread_id = thread_id
		blank_thread_store.message_ts = event['ts']
		blank_thread_store.slack_user_id = event['user']
		blank_thread_store.commit(name=f"{user.name} - {datetime.datetime.now().strftime('%X')}")

		output_message = slack_app.client.chat_update(
			text=f"Thread saved to database with ID: {thread_id} and TS: {event['ts']}, now running the thread...",
			channel=event['channel'],
			ts=output_message['ts'],
		).data

		# Run the thread
		run = openai.utils.run_thread(thread.id, blank_thread_store.ASSISTANT_ID)
		status_message = say(f"Thread is running, status: {run.status}", thread_ts=event['ts'])

		slack_tasks.ai_threads.check_run(
			thread_id=thread_id,
			run_id=run.id,
			status_message_ts=status_message['ts'],
			channel_id=event['channel']
		)

	elif event['channel'] in desired_channels and 'thread_ts' in event:
		# Add the message to the OpenAI thread
		try:
			thread_store = monday.items.ai_threads.InvoiceAssistantThreadItem.get_by_message_ts(event['thread_ts'])
		except monday.api.items.MondayAPIError as e:
			say(f"Error: {e}", thread_ts=event['ts'])
			return

		message = openai.utils.add_message_to_thread(thread_store.thread_id.value, event['text'])
		run = openai.utils.run_thread(thread_store.thread_id.value, thread_store.ASSISTANT_ID)
		status_message = say("Message added to thread, running thread...", thread_ts=event['ts'])

		slack_tasks.ai_threads.check_run(
			thread_id=thread_store.thread_id.value,
			run_id=run.id,
			status_message_ts=status_message['ts'],
			channel_id=event['channel']
		)

	else:
		# some other error
		say("Error: Invalid Channel or Thread", thread_ts=event['ts'])


