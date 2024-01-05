import json
import pytest
from unittest.mock import Mock, patch

# Replace 'your_module' with the actual name of your module/package
from app.models.product import ProductModel, MissingProductData

# A fixture that creates a mock for Redis connection and MondayClient
@pytest.fixture
def mock_services():
	with patch('app.models.base.get_redis_connection') as mock_redis, \
			patch('app.models.base.get_items') as mock_client:
		mock_redis.return_value.get.return_value = None  # simulate cache miss
		mock_redis.return_value.mget.return_value = [None]  # simulate cache miss on multiple get
		mock_client.get_items.return_value = [Mock(price=100, device_connect=[123])]  # mock moncli.en.Item
		yield mock_redis, mock_client


@pytest.fixture
def product_model_data():
	return {
		'price': 100,
		'name': 'Test Product',
		'device_id': 123,
	}


def test_product_initialization_with_moncli_item(mock_services, product_model_data):
	mock_redis, mock_client = mock_services
	item_id = 123
	mock_item = Mock()
	mock_item.id = item_id
	mock_item.price = product_model_data['price']
	mock_item.name = product_model_data['name']
	mock_item.device_connect = [product_model_data['device_id']]

	model = ProductModel(item_id, mock_item)

	assert model.id == item_id
	assert model.price == product_model_data['price']
	assert model.name == product_model_data['name']
	assert model.device_id == product_model_data['device_id']


def test_product_initialization_without_moncli_item(mock_services, product_model_data):
	mock_redis, mock_client = mock_services
	item_id = 123

	model = ProductModel(item_id)

	assert model.id == item_id
	# Accessing properties triggers data fetch and cache
	assert model.price == product_model_data['price']
	assert model.name == product_model_data['name']
	assert model.device_id == product_model_data['device_id']
	mock_client.get_items.assert_called_once_with(ids=[item_id], get_column_values=True)


def test_product_save_to_cache(mock_services, product_model_data):
	mock_redis, mock_client = mock_services
	item_id = 123

	model = ProductModel(item_id)
	model.price  # Access to initiate fetching and caching

	# Validate that the cache set was called with serialized data
	expected_cache_data = json.dumps(product_model_data)
	cache_key = f"product:{item_id}"
	mock_redis.return_value.set.assert_called_once_with(cache_key, expected_cache_data)


def test_missing_product_data(mock_services):
	mock_redis, mock_client = mock_services
	item_id = 123
	mock_redis.return_value.get.return_value = json.dumps({'name': 'Missing Price'})  # partial data

	model = ProductModel(item_id)

	# Verify that accessing a missing value raises an error
	with pytest.raises(MissingProductData) as exc_info:
		_ = model.price
	assert 'price' in str(exc_info.value)