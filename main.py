import logging
import os

import app

log = logging.getLogger('eric')

env = os.getenv('ENV', 'development')
port = int(os.environ.get('PORT', 8000))  # Default to 8000 for local development

eric = app.create_app()


if __name__ == '__main__':
	if env == 'production':
		eric.run()
	elif env == 'testing':
		eric.run()
	elif env == 'development':
		from app.services.monday import api
		i = api.get_api_items([6223483200])[0]
		si = api.get_api_items([6223575653])[0]
		main = api.get_api_items([6223483200])[0]
	else:
		raise Exception(f"Invalid ENV: {env}")
