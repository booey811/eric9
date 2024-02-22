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
		from app.utilities import users
		from app.services import gcal
		from app.services import monday, slack
		from app import tasks
		gabe = users.User('gabe')

		# r = slack.builders.DeviceAndProductView().create_device_and_product_blocks()
		from app.cache.utilities import build_product_cache, build_device_cache
		build_product_cache()

	else:
		raise Exception(f"Invalid ENV: {env}")
