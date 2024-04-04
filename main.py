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
		from app.services import monday
		from app.utilities import tools
		tools.MondayTools.list_redundant_columns(985177480)
	else:
		raise Exception(f"Invalid ENV: {env}")
