import logging
from logging.handlers import RotatingFileHandler
import os

from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv()


def configure_logging(config_name):
	# Create a custom logger
	logger = logging.getLogger('eric')
	logger.propagate = False  # To prevent double logging

	if not logger.handlers:

		# Create handlers
		c_handler = logging.StreamHandler()

		# Create formatters and add it to handlers
		c_format = logging.Formatter(
			'%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
		)

		c_handler.setFormatter(c_format)

		# Set the level and add handlers
		if config_name == 'development':
			logger.setLevel(logging.DEBUG)
			c_handler.setLevel(logging.DEBUG)
		elif config_name == 'production':
			logger.setLevel(logging.WARNING)
			c_handler.setLevel(logging.WARNING)
		elif config_name == 'testing':
			logger.setLevel(logging.ERROR)
			c_handler.setLevel(logging.ERROR)

		# Add handlers to the logger
		logger.addHandler(c_handler)

	return logger


class Config(object):
	"""Base config, uses staging database server."""
	DEBUG = False
	TESTING = False
	DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///default.db'
	SECRET_KEY = os.environ.get('SECRET_KEY') or 'default-secret-key'
	REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'


class ProductionConfig(Config):
	"""Uses production database server."""
	DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///production.db'


class DevelopmentConfig(Config):
	"""Uses development database server and enables debug mode."""
	DEBUG = True
	DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///development.db'
	REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/3'


class TestingConfig(Config):
	"""Uses a separate database for tests and enables testing mode."""
	TESTING = True
	DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///testing.db'
