from app.redis_client import redis_connection_pool, get_redis_connection


def post_worker_init(worker):
	# Call the function to ensure the connection pool is set
	get_redis_connection()
	worker.log.info("Initialized Redis connection pool")
