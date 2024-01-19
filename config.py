import logging
from logging.handlers import RotatingFileHandler
import os

from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv()


def get_config(env=None):
	if not env:
		env = os.environ["ENV"]
	conf = ENV_CONFIG_DICT.get(env)
	if not conf:
		raise Exception(f"Invalid config: {env}")

	return conf


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
		logger.setLevel(os.environ['LOG_LEVEL'])
		c_handler.setLevel(os.environ['LOG_LEVEL'])

		# Add handlers to the logger
		logger.addHandler(c_handler)

	return logger


class Config(object):
	"""Base config, uses staging database server."""
	CONFIG = "BASE"
	DEBUG = False
	TESTING = False
	REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'

	SLACK_APP_TOKEN = os.environ.get("SLACK_BOT")  # icorrect workspace
	SLACK_DEV_CHANNEL = "C036M43NBR6"  # icorrect workspace: dev-testing
	SLACK_ERROR_CHANNEL = "C06EYFD359P"  # icorrect-workspace: eric9:errors

	# MONDAY BOARD IDS
	MONDAY_MAIN_BOARD_ID = 349212843
	MAIN_DEV_GROUP_ID = "new_group49546"
	TEST_PROOF_ITEMS = "new_group26478"

	# MONDAY KEYS
	MONDAY_KEYS = {
		"system": os.environ["MON_SYSTEM"],
	}

	# MOTION KEYS
	MOTION_KEYS = {
		"gabe": os.environ["MOTION_GABE"],
		"dev": os.environ["MOTION_DEV"],
	}

	def get_vars(self):
		return (
			f"CONFIG: {self.CONFIG}",
			f"DEBUG: {self.DEBUG}",
			f"TESTING: {self.TESTING}",
			f"DATABASE_URI: {self.DATABASE_URI}",
			f"SECRET_KEY: {self.SECRET_KEY}",
			f"REDIS_URL: {self.REDIS_URL}",
			f"SLACK_APP_TOKEN: {self.SLACK_APP_TOKEN}",
		)


class ProductionConfig(Config):
	"""Uses production database server."""
	CONFIG = "PRODUCTION"
	DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///production.db'
	SLACK_APP_TOKEN = os.environ["SLACK_BOT"]  # icorrect workspace


class DevelopmentConfig(Config):
	"""Uses development database server and enables debug mode."""
	CONFIG = "DEVELOPMENT"
	DEBUG = True
	DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///development.db'
	REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/3'

	SLACK_APP_TOKEN = os.environ.get("SLACK_DEV_BOT")  # dev workspace
	SLACK_DEV_CHANNEL = "C037P4MLAF4"  # dev workspace: dev-testing
	SLACK_ERROR_CHANNEL = "C047C1L0WLW"  # dev-workspace: reporting


class TestingConfig(Config):
	"""Uses a separate database for tests and enables testing mode."""
	CONFIG = "TESTING"
	TESTING = True
	DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///testing.db'


ENV_CONFIG_DICT = {
	"development": DevelopmentConfig,
	"production": ProductionConfig,
	"testing": TestingConfig
}
