import os
import logging
from logging.handlers import RotatingFileHandler
import traceback

from flask import Flask, jsonify

import config
from config import get_config
from .services.slack import slack_client, blocks
from .errors import EricError

env = os.getenv('ENV', 'development')
logger = config.configure_logging(env)

conf = get_config(env)


def create_app():
	app = Flask(__name__)
	app.logger = logger
	app.config.from_object(conf)

	@app.errorhandler(EricError)
	def handle_uncaught_exception(error):
		# Log the full stack trace, but do not send it to the client for security reasons
		trace = traceback.format_exc()
		logger.error(f'Eric Exception: {trace}')

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
	from .routes import scheduling, r_tests, ai_routes, slack
	app.register_blueprint(scheduling.scheduling_bp)
	app.register_blueprint(r_tests.test_bp)
	app.register_blueprint(ai_routes.ai_bp)

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
