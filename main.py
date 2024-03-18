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
		from app.tasks.monday import stock_control
		stock_control.update_stock_checkouts(4819915342)
		stock_control.process_stock_checkout(6278365602)
	else:
		raise Exception(f"Invalid ENV: {env}")
