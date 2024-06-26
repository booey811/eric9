import os
import traceback

from flask import Flask, jsonify

import config
from config import get_config
from .services.slack import slack_client, blocks
from .errors import EricError
from .utilities import notify_admins_of_error

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
	from .routes import (scheduling, slack, monday as monday_routes, ai as ai_routes, zendesk as zendesk_routes,
						 admin_routes, xero_webhooks)

	app.register_blueprint(scheduling.scheduling_bp)
	app.register_blueprint(ai_routes.ai_bp)
	app.register_blueprint(monday_routes.main_board.main_board_bp)
	app.register_blueprint(monday_routes.typeform.typeform_bp)
	app.register_blueprint(ai_routes.ai_blogs_bp)
	app.register_blueprint(monday_routes.sessions.sessions_bp)
	app.register_blueprint(monday_routes.misc.monday_misc_bp)
	app.register_blueprint(monday_routes.stock_control.stock_control_bp)
	app.register_blueprint(zendesk_routes.zendesk_bp)
	app.register_blueprint(monday_routes.financial.monday_sales_bp)
	app.register_blueprint(monday_routes.repair_process.repair_process_bp)
	app.register_blueprint(admin_routes.admin_bp)
	app.register_blueprint(xero_webhooks.xero_bp)
	return app
