import os

from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)


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
