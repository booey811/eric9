import os
import logging
from logging.handlers import RotatingFileHandler
import traceback

from flask import Flask, jsonify

import config

env = os.getenv('ENV', 'development')
logger = config.configure_logging(env)


def create_app(config_name):
	conf = config.get_config(config_name)
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
	from .services.monday import routes

	return app


def notify_admins_of_error(trace):
	# Integrate with an error notification tool (e.g., email, Slack, PagerDuty)
	# This function is where you would include your custom notification logic
	print(trace)


class EricError(Exception):
	"""Base error for the application"""


class DataError(EricError):

	def __init__(self, message):
		self.message = message

	def __str__(self):
		return f"DataError: {self.message}"
