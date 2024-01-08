import os

import app

import config

env = os.getenv('ENV', 'testing')
port = int(os.environ.get('PORT', 8000))  # Default to 8000 for local development
conf = config.get_config(env)
if env != 'production':
	for v in conf().get_vars():
		print(v)

eric = app.create_app(env)


if __name__ == '__main__':
	if env == 'production':
		pass
	elif env == 'testing':
		pass
	elif env == 'development':
		from app.models import ProductModel
		from app.cache import get_redis_connection, CacheMiss
		from app.cache.utilities import build_product_cache
		from app.models.main_item import MainModel
		from app.services import motion
		from app.services import monday
		from pprint import pprint as p
		main_board = monday.client.get_board(349212843)
		dev_group = main_board.get_group(id="new_group99626")
		items = monday.get_items([item.id for item in dev_group.items], column_values=True)
		for item in items:
			m = MainModel(item.id, item)
			print(f"Got {m.model.name}")
			try:
				deadline = m.model.hard_deadline.isoformat()
			except AttributeError:
				deadline = None
			print(f"Deadline: {deadline}")
			r = motion.client.create_task(
				name=m.model.name,
				deadline=deadline,
				description=m.model.description
			)
			p(r)

	else:
		raise Exception(f"Invalid ENV: {env}")
