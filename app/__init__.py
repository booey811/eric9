import os

from flask import Flask

from config import DevelopmentConfig, ProductionConfig, TestingConfig

# Set configuration from environment variable or default to DevelopmentConfig
ENV_CONFIG_DICT = {
	"development": DevelopmentConfig,
	"production": ProductionConfig,
	"testing": TestingConfig
}


def create_app():
	app = Flask(__name__)
	config_name = os.getenv('ENV', 'development')
	app.config.from_object(ENV_CONFIG_DICT.get(config_name))

	# Here, import and register blueprints

	return app


class EricError(Exception):
	"""Base error for the application"""
