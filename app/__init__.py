import os
import logging
from logging.handlers import RotatingFileHandler
import traceback

from flask import Flask, jsonify

import config
from config import get_config
from .services.slack import slack_client, blocks

env = os.getenv('ENV', 'development')
logger = config.configure_logging(env)

conf = get_config(env)


def create_app(config_name):
	app = Flask(__name__)
	app.logger = logger
	app.config.from_object(conf)

	@app.errorhandler(Exception)
	def handle_uncaught_exception(error):
		# Log the full stack trace, but do not send it to the client for security reasons
		trace = traceback.format_exc()
		logger.error(f'Unhandled Exception: {trace}')

		# Here you can integrate a notification service to notify you of the exception details
		notify_admins_of_error(trace)

		# Return a generic "internal server error" response
		response = jsonify({
			'status': 'error',
			'message': 'An unexpected error occurred. Our engineers have been informed.'
		})
		response.status_code = 500
		return response

	# Here, import and register blueprints
	from .routes import scheduling, r_tests
	app.register_blueprint(scheduling.scheduling_bp)
	app.register_blueprint(r_tests.test_bp)

	return app


def notify_admins_of_error(trace):
	# Integrate with an error notification tool (e.g., email, Slack, PagerDuty)
	# This function is where you would include your custom notification logic
	s_blocks = [
		blocks.add.text_block("Error"),
		blocks.add.text_block(trace)
	]
	slack_client.chat_postMessage(
		channel=conf.SLACK_ERROR_CHANNEL,
		text='eric9:Unhandled Error',
		blocks=s_blocks
	)


class EricError(Exception):
	"""Base error for the application"""


class DataError(EricError):

	def __init__(self, message):
		self.message = message

	def __str__(self):
		return f"DataError: {self.message}"
