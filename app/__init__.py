from flask import Flask
from dotenv import load_dotenv
import os

# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)


def create_app(config_filename=None):
	app = Flask(__name__)

	# Load default configuration or from the provided filename
	if config_filename:
		app.config.from_pyfile(config_filename)
	else:
		app.config.from_mapping(
			# Default config or environment variables
		)

	# Here, import and register your blueprints

	# Return the app instance
	return app


class EricError(Exception):
	"""Base error for the application"""
