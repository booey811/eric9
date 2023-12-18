import os
import redis

import app

redis_connection_pool = None


def setup_redis_connection_pool():
	global redis_connection_pool
	redis_connection_pool = redis.ConnectionPool.from_url(app.ENV_CONFIG_DICT[os.environ['ENV']].REDIS_URL)


def get_redis_connection():
	if redis_connection_pool is None:
		# Assuming Gunicorn has not been initialized, use environment variable.
		setup_redis_connection_pool()
	return redis.StrictRedis(connection_pool=redis_connection_pool)
