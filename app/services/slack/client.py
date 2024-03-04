import os

from slack_sdk import WebClient
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import config

conf = config.get_config()

slack_app = App(token=conf.SLACK_BOT, signing_secret=conf.SLACK_SIGNING_SECRET)
slack_client = slack_app.client

if os.environ['SLACK_SOCKET'] == 'on' and os.environ['PROC_TYPE'] == 'web':
	handler = SocketModeHandler(slack_app, conf.SLACK_APP)
	handler.connect()
