# Desc: Utility functions for the application

import config


def notify_admins_of_error(trace):
	from ..services.slack import blocks, slack_client
	# Integrate with an error notification tool (e.g., email, Slack, PagerDuty)
	# This function is where you would include your custom notification logic

	def make_block(content):
		return {
			"type": "rich_text",
			"elements": [
				{
					"type": "rich_text_section",
					"elements": [
						{
							"type": "text",
							"text": content
						}
					]
				}
			]
		}

	s_blocks = [
		make_block(f"An error occurred in the application: {trace}")
	]

	slack_client.chat_postMessage(
		channel=config.get_config().SLACK_ERROR_CHANNEL,
		text='eric9:Unhandled Error',
		blocks=s_blocks
	)
