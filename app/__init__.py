import os

from flask import Flask

import config

# Set configuration from environment variable or default to DevelopmentConfig
ENV_CONFIG_DICT = {
	"development": config.DevelopmentConfig,
	"production": config.ProductionConfig,
	"testing": config.TestingConfig
}


def create_app():
	app = Flask(__name__)
	config_name = os.getenv('ENV', 'development')
	app.config.from_object(ENV_CONFIG_DICT.get(config_name))

	# Here, import and register blueprints

	return app


class EricError(Exception):
	"""Base error for the application"""
