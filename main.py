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
		from app.services.zendesk import helpers
		from app.utilities import notify_admins_of_error
		from app.services.slack import exceptions as s, helpers as s_help
		from app.cache.utilities import build_device_cache
		build_device_cache()

	else:
		raise Exception(f"Invalid ENV: {env}")
