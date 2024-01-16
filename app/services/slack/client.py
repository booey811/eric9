import os

import config

from slack_sdk import WebClient

conf = config.get_config(os.environ['ENV'])

slack_client = WebClient(token=conf.SLACK_APP_TOKEN)
