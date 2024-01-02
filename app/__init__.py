import os
import logging
from logging.handlers import RotatingFileHandler

from quart import Quart

import config

env = os.getenv('ENV', 'development')
logger = config.configure_logging(env)

# Set configuration from environment variable or default to DevelopmentConfig
ENV_CONFIG_DICT = {
	"development": config.DevelopmentConfig,
	"production": config.ProductionConfig,
	"testing": config.TestingConfig
}


def create_app(config_name):
	conf = ENV_CONFIG_DICT.get(config_name)

	app = Quart(__name__)
	app.logger = logger
	from quart import request, got_request_exception

	# Example to log every request
	@app.before_request
	async def before_request():
		logger.info(f"Request starting: {request.method} {request.path}")

	# Example to log responses
	@app.after_request
	async def after_request(response):
		logger.info(f"Request complete: {response.status_code}")
		return response

	# Log exceptions
	@got_request_exception.connect
	async def handle_exception(sender, exception):
		logger.error(f"Unhandled Exception: {exception}")

	if config_name == 'development':
		pass
	elif config_name == 'production':
		pass

	logger.info(f"Creating App in {config_name} env; {__name__}")
	app.config.from_object(conf)
	logger.debug(f"{config_name} config loaded")

	# Here, import and register blueprints
	from .services.monday import routes

	app.register_blueprint(routes.test_bp)

	return app


class EricError(Exception):
	"""Base error for the application"""
