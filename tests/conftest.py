import pytest
import redis

from app.redis_client import get_redis_connection


@pytest.fixture(scope='function')
def redis_client():
	# Assuming you have a separate Redis database for testing (db=1)
	client = redis.StrictRedis(connection_pool=get_redis_connection())

	# Flush the database before each test
	client.flushdb()

	yield client  # Provide the client to the test

# Optional: Flush the database after the test runs. You can use this if your
# tests rely on checking the state of Redis after execution.
# client.flushdb()
