import logging
import os

import app

import config

log = logging.getLogger('eric')

env = os.getenv('ENV', 'testing')
port = int(os.environ.get('PORT', 8000))  # Default to 8000 for local development
conf = config.get_config(env)
if env != 'production':
	for v in conf().get_vars():
		log.debug(v)

eric = app.create_app(env)


if __name__ == '__main__':
	if env == 'production':
		eric.run()
	elif env == 'testing':
		pass
	elif env == 'development':
		pass
	else:
		raise Exception(f"Invalid ENV: {env}")
