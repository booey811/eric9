import os
import json
from pprint import pprint
import tempfile
import config

from ...errors import EricError
from ...cache import get_redis_connection
from .client import slack_client

conf = config.get_config()


def save_metadata(meta, key_name):
	"""saves current app metadata to cache for retrieval if needed"""
	key = f"slack_meta:{key_name}"
	get_redis_connection().set(
		name=key,
		value=json.dumps(meta),
		ex=86400  # 1 day
	)
	return True


def dump_slack_view_data(view):
	with tempfile.NamedTemporaryFile(delete=False) as temp:
		# Write the error message and stack trace to the file
		view = json.dumps(view, indent=4)
		temp.write(f"An Error Occurred in Slack\n\n{view}".encode())

	# Send the file to Slack
	with open(temp.name, 'rb') as file_content:
		slack_client.files_upload_v2(
			channel=config.get_config().SLACK_DUMP_CHANNEL,
			file=file_content,
			filename='view_dump.txt'
		)


class SlackDataError(EricError):

	def __str__(self):
		return f"Slack Data Error: {self.message}"
