# Desc: Utility functions for the application

import config
import traceback
import os
import tempfile

from . import users, tools


def notify_admins_of_error(error):
	from ..services.slack import blocks, slack_client
	# Integrate with an error notification tool (e.g., email, Slack, PagerDuty)
	# This function is where you would include your custom notification logic

	# Get the stack trace
	trace = traceback.format_exc()

	# Create a temporary file
	with tempfile.NamedTemporaryFile(delete=False) as temp:
		# Write the error message and stack trace to the file
		temp.write(f"An error occurred: {error}\n\nStack trace:\n{trace}".encode())

	# Send the file to Slack
	with open(temp.name, 'rb') as file_content:
		slack_client.files_upload_v2(
			channel=config.get_config().SLACK_ERROR_CHANNEL,
			file=file_content,
			filename='error_log.txt'
		)
