import os
import logging
from logging.handlers import RotatingFileHandler

from quart import Quart

import config

# Set configuration from environment variable or default to DevelopmentConfig
ENV_CONFIG_DICT = {
	"development": config.DevelopmentConfig,
	"production": config.ProductionConfig,
	"testing": config.TestingConfig
}


def create_app(config_name):
	app = Quart(__name__)
	app.config.from_object(ENV_CONFIG_DICT.get(config_name))

	# Here, import and register blueprints
	from .services.monday import routes
	app.register_blueprint(routes.blueprint)

	# logging config
	formatter = logging.Formatter(
		"%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
	)

	if config_name == 'development':
		app.logger.setLevel(logging.DEBUG)
		handler = logging.StreamHandler()

		handler.setFormatter(formatter)
		app.logger.addHandler(handler)

	elif config_name == 'production':
		# Production logger configuration
		app.logger.setLevel(logging.WARNING)

		# File logging
		if not os.path.exists('logs'):
			os.mkdir('logs')

		file_handler = RotatingFileHandler(
			'logs/myapp.log',
			maxBytes=10240,
			backupCount=10
		)

		file_handler.setFormatter(formatter)
		app.logger.addHandler(file_handler)

	return app


class EricError(Exception):
	"""Base error for the application"""
