# Desc: Utility functions for the application

import config


def notify_admins_of_error(trace):
	from ..services.slack import blocks, slack_client
	# Integrate with an error notification tool (e.g., email, Slack, PagerDuty)
	# This function is where you would include your custom notification logic
	s_blocks = [
		blocks.add.text_block("Error"),
		blocks.add.text_block(trace)
	]
	slack_client.chat_postMessage(
		channel=config.get_config().SLACK_ERROR_CHANNEL,
		text='eric9:Unhandled Error',
		blocks=s_blocks
	)
