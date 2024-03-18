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
		pass
		from app.services import stuart
		from app.tasks.stuart import book_courier
		book_courier(6276128077, 'incoming')
	else:
		raise Exception(f"Invalid ENV: {env}")
