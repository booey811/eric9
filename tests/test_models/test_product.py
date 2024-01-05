import json
import pytest
from unittest.mock import Mock, patch
from app.models.product import ProductModel, MissingProductData


# Helper function to create a mock Moncli item
def create_mock_moncli_item(product_id, price, device_id):
	mock_item = Mock()
	mock_item.id = product_id
	mock_item.name = f"Product {product_id}"
	mock_item.price = price
	mock_item.device_connect = [device_id]
	return mock_item


# Fixture to mock Redis connection
@pytest.fixture
def mock_redis():
	with patch('app.models.base.get_redis_connection') as mock_conn:
		mock_instance = Mock()
		mock_conn.return_value = mock_instance
		yield mock_instance


# Fixture to mock Moncli get_items
@pytest.fixture
def mock_get_items():
	with patch('app.models.base.get_items') as mock_get_items:
		yield mock_get_items


@pytest.fixture
def product_data():
	return {
		'price': 100,
		'device_id': '12345',
	}


@pytest.fixture
def product_id():
	return "123"


def test_get_from_cache_hit(mock_redis, product_data, product_id):
	cache_data = product_data.copy()
	cache_data['name'] = f"Product {product_id}"
	mock_redis.get.return_value = json.dumps(cache_data)

	product = ProductModel(product_id)
	cached_data = product.get_from_cache()

	assert cached_data == cache_data
	mock_redis.get.assert_called_once_with(product.cache_key)
