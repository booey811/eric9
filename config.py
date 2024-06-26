import logging
from logging.handlers import RotatingFileHandler
import os
import holidays

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


def get_public_holidays():
	"""utilises holidays library to provide a list of public holiday dates in UK, currently only for 2023"""
	hols = holidays.country_holidays(country='GB', subdiv='England', years=2023)
	return hols


class Config(object):
	"""Base config, uses staging database server."""
	CONFIG = "BASE"
	APP_URL = "http://localhost:8000"
	DEBUG = False
	TESTING = False
	REDIS_URL = 'redis://localhost:6379/0'

	OPENAI_KEY = os.environ["OPENAI_API_KEY"]

	OPEN_AI_ASSISTANTS = {
		"enquiry": "asst_RLYPxU9Qdkpj4btu0bLQbJ1s",
		"translator": "asst_PNMO7wrcHrAM1ViORqJ7oev1",
		"blog_writer": "asst_0rjt5WqfAUw2NLqroLgZdxZo"
	}

	SLACK_BOT = os.environ["SLACK_BOT"]  # icorrect workspace
	SLACK_APP = os.environ['SLACK_APP']  # icorrect workspace
	SLACK_SIGNING_SECRET = os.environ["SLACK_SECRET"]  # icorrect workspace
	SLACK_DEV_CHANNEL = "C036M43NBR6"  # icorrect workspace: dev-testing
	SLACK_ERROR_CHANNEL = "C06EYFD359P"  # icorrect-workspace: eric9:errors
	SLACK_DUMP_CHANNEL = "C04DD337JTT"  # icorrect-workspace: eric9:dumps
	SLACK_AI_INVOICE_CHANNEL = "C04D4049Y72"  # icorrect-workspace: eric9:eric-quotes
	SLACK_SHOW_META = os.environ['SHOW_META']

	# MONDAY BOARD IDS
	MONDAY_MAIN_BOARD_ID = 349212843
	MAIN_DEV_GROUP_ID = "new_group49546"
	TEST_PROOF_ITEMS = "new_group26478"
	UNDER_REPAIR_GROUP_ID = "new_group22081"
	TODAYS_REPAIRS_GROUP_ID = "new_group70029"

	MONDAY_TEST_ITEM_IDS = {
		"parts": [
			2101356466,  # TEST BATTERY PART ITEM
			2109687361,  # TEST PART ITEM
			3607830355,  # TEST SCREEN PART ITEM
		],
		"devices": [
			3926445975,  # Test device
		],
		"products": [
			3331258333,  # TEST BATTEY PRODUCT
			3607829530,  # TEST GLASS TOUCH PRODUCT
			3607829981,  # TEST DISPLAY PRODUCT
		]
	}

	# MONDAY KEYS
	MONDAY_KEYS = {
		"system": os.environ["MON_SYSTEM"],
		"gabe": os.environ['MON_GABE'],  # for using the new API
	}

	# MOTION KEYS
	MOTION_KEYS = {
		"gabe": os.environ["MOTION_GABE"],
		"dev": os.environ["MOTION_DEV"],
		"safan": os.environ['MOTION_SAFAN'],
		'andres': os.environ['MOTION_ANDRES'],
		"ferrari": os.environ['MOTION_GABE'],
		"dev-slack-workspace": os.environ['MOTION_GABE'],
		"ricky": os.environ['MOTION_GABE'],
		"kae": os.environ['MOTION_GABE'],
	}

	# MOTION REFERENCES
	TEAM_WORKSPACE_ID = "Xw5FG8E5tGNYByGOI5Ucx"

	TYPEFORM_API_KEY = os.environ["TYPEFORM_API_KEY"]

	PUBLIC_HOLIDAYS = get_public_holidays()
	ICORRECT_HOLIDAYS = [

	]  # list of lists, all objects are dates that signify start and end times

	STUART_ENV = "sandbox"
	STUART_CLIENT_ID = os.environ['STUART_ID_SAND']
	STUART_CLIENT_SECRET = os.environ['STUART_SECRET_SAND']

	ICORRECT_ADDRESS_INFO = {
		"address": "12 Margaret Street",
		"postcode": "W1W 8JQ",
		"collection_contact": "Kae Aziz",
	}

	AI_CHANNEL_IDS = {
		"invoices": "C074NRQ94G0"  # dev-workspace: ai-invoices
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
	APP_URL = "https://eric9-c2d6de2066d6.herokuapp.com"

	REDIS_URL = os.environ.get('REDIS_URL')

	STUART_ENV = 'production'
	STUART_CLIENT_ID = os.environ['STUART_ID_PROD']
	STUART_CLIENT_SECRET = os.environ['STUART_SECRET_PROD']

	AI_CHANNEL_IDS = {
		"invoices": "C06954NEQ4W"  #icorrect-workspace: eric9:ai-assistant
	}


class DevelopmentConfig(Config):
	"""Uses development database server and enables debug mode."""
	CONFIG = "DEVELOPMENT"
	DEBUG = True
	DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///development.db'
	REDIS_URL = 'redis://localhost:6379/0'

	SLACK_BOT = os.environ.get("SLACK_DEV_BOT")  # dev workspace: eric9-dev
	SLACK_APP = os.environ.get("SLACK_DEV_APP")  # dev workspace
	SLACK_SIGNING_SECRET = os.environ.get("SLACK_DEV_SECRET")  # dev workspace
	SLACK_DEV_CHANNEL = "C037P4MLAF4"  # dev workspace: dev-testing
	SLACK_DUMP_CHANNEL = "C04DG52S00H"
	SLACK_ERROR_CHANNEL = "C047C1L0WLW"  # dev-workspace: reporting


class TestingConfig(Config):
	"""Uses a separate database for tests and enables testing mode."""
	CONFIG = "TESTING"
	TESTING = True
	DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///testing.db'
	REDIS_URL = 'redis://localhost:6379/0'

	SLACK_BOT = os.environ.get("SLACK_DEV_BOT")  # dev workspace
	SLACK_APP = os.environ.get("SLACK_DEV_APP")  # dev workspace
	SLACK_SIGNING_SECRET = os.environ.get("SLACK_DEV_SECRET")  # dev workspace
	SLACK_DEV_CHANNEL = "C037P4MLAF4"  # dev workspace: dev-testing
	SLACK_ERROR_CHANNEL = "C047C1L0WLW"  # dev-workspace: reporting
	SLACK_AI_INVOICE_CHANNEL = "C074NRQ94G0"  # dev-workspace: ai-invoices


ENV_CONFIG_DICT = {
	"development": DevelopmentConfig,
	"production": ProductionConfig,
	"testing": TestingConfig
}
