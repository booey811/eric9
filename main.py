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
		from app.tasks import sync_platform
		from app.tasks.monday import typeform
		typeform.sync_typeform_response_with_monday(6212761255)
		# sync_platform.sync_to_monday(25919)
	else:
		raise Exception(f"Invalid ENV: {env}")
