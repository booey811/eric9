from slack_sdk import WebClient

import config

conf = config.get_config()

slack_client = WebClient(token=conf.SLACK_APP_TOKEN)
