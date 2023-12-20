from app.cache.redis_client import get_redis_connection


def post_worker_init(worker):
	# Call the function to ensure the connection pool is set
	get_redis_connection()
	worker.log.info("Initialized Redis connection pool")
