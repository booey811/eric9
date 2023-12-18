# redis_client.py
import os
import redis

redis_connection_pool = None


def setup_redis_connection_pool():
	global redis_connection_pool
	redis_connection_pool = redis.ConnectionPool.from_url(os.environ["REDIS_URL"])


def get_redis_connection():
	if redis_connection_pool is None:
		# Assuming Gunicorn has not been initialized, use environment variable.
		setup_redis_connection_pool()
	return redis.StrictRedis(connection_pool=redis_connection_pool)
