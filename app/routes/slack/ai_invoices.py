from pprint import pprint as p

from ...services.slack import slack_app
from ...services import monday, openai

import config

conf = config.get_config()


class SlackAIThreadAdapter:
	"""this object is used to adapt slack threads to the AI invoice assistant, retrieving the desired thread where
	needed"""

	def __init__(self, slack_message):
		self.message_data = slack_message

	def get_thread_from_message_ts(self, slack_message_ts):
		"""get the thread from a Slack message timestamp. Raises an exception if the thread is not found"""
		pass

	def create_new_thread_storage(self, slack_message_ts):
		"""create a new thread storage in monday for the AI invoice assistant"""
		pass


@slack_app.event("message")
def handle_new_message(client, event):
	# List of desired channels
	desired_channels = ['channel1_id', 'channel2_id', 'channel3_id']

	# Check if the event is from one of the desired channels and is not a threaded reply
	if event['channel'] in desired_channels and 'thread_ts' not in event:
		# Create a new thread in OpenAI's API
		thread = openai.utils.create_thread()
		thread_id = thread.id

		# Create a new item on a Monday board
		monday.create_item({
			'slack_message_ts': event['ts'],
			'openai_thread_id': thread_id
		})

	elif event['channel'] in desired_channels and 'thread_ts' in event:
		# Add the message to the OpenAI thread
		thread_id = monday.get_item_by_slack_message_ts(event['thread_ts'])['openai_thread_id']
		openai.utils.add_message_to_thread(thread_id, event['text'])

		# Complete a run
		result = openai.utils.complete_run(thread_id)

		# Post the result as a reply to the original message
		try:
			web_client.chat_postMessage(
				channel=event['channel'],
				text=result,
				thread_ts=event['thread_ts']
			)
		except SlackApiError as e:
			print(f"Error posting message: {e}")


