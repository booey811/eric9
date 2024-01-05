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
		get_redis_connection().flushall()

	else:
		raise Exception(f"Invalid ENV: {env}")
