import pytest
from unittest.mock import Mock, patch

# Assuming your product retrieval function is in the module `product_utils.py`
from product_utils import retrieve_product


# Set up the mock for Redis
@pytest.fixture
def mock_redis():
	with patch('redis.StrictRedis') as mock:
		yield mock


# Set up the mock for monday.com API client
@pytest.fixture
def mock_monday_client():
	with patch('monday.MondayClient') as mock:
		yield mock


# This fixture sets up your product retrieval function, using the above mocks
@pytest.fixture
def product_retrieval(mock_redis, mock_monday_client):
	return lambda product_id: retrieve_product(product_id, mock_redis, mock_monday_client)


def test_retrieves_from_cache_first(mock_redis, product_retrieval):
	product_id = '123'
	mock_redis.get.return_value = '{"name": "Product 123"}'  # Mock cached data

	product = product_retrieval(product_id)

	mock_redis.get.assert_called_with(product_id)  # Check if cache was accessed
	assert product['name'] == 'Product 123'  # Confirm the product was retrieved from the cache


def test_falls_back_to_monday_if_no_cache(mock_redis, mock_monday_client, product_retrieval):
	product_id = '123'
	mock_redis.get.return_value = None  # No cached data
	mock_monday_client.get_item_by_id.return_value = {'name': 'Product 123'}  # Mock monday.com response

	product = product_retrieval(product_id)

	mock_redis.get.assert_called_with(product_id)  # Confirm cache was checked
	mock_monday_client.get_item_by_id.assert_called_with(product_id)  # Confirm monday.com was queried
	assert product['name'] == 'Product 123'  # Confirm the correct product was retrieved


def test_caches_monday_data_when_not_already_cached(mock_redis, mock_monday_client, product_retrieval):
	product_id = '123'
	mock_redis.get.return_value = None  # No cached data
	monday_response = {'name': 'Product 123'}  # Mock monday.com response

	mock_monday_client.get_item_by_id.return_value = monday_response

	product = product_retrieval(product_id)

	# Note: You may need to serialize your monday.com response data before caching it
	mock_redis.set.assert_called_once_with(product_id, str(monday_response))
	assert product == monday_response  # Confirm the correct product was retrieved

# Add more tests as needed
