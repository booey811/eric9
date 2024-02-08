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
		item_data = monday.api.get_api_items([5799427883])
		item = monday.items.MainItem(item_data[0]['id'], item_data[0])
		print(item.url_link.value)
	else:
		raise Exception(f"Invalid ENV: {env}")
