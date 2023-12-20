import json
import pytest
from unittest.mock import patch, MagicMock

from app.models.product import ProductModel, MondayError, _BaseProductModel
import app.services.monday as monday_module
from moncli.entities import Item

# Sample data for the mock to return
product_id = '123'
product_data = {'id': product_id, 'price': 100.0, 'name': 'Sample Product'}
cached_product_data = json.dumps(product_data).encode('utf-8')


# This is the mock_cache setup
@pytest.fixture
def mock_cache():
	with patch('app.models.product.get_redis_connection') as mock_cache:
		mock_instance = MagicMock()
		mock_instance.get.return_value = cached_product_data
		mock_cache.return_value = mock_instance
		yield mock_instance


@pytest.fixture
def mock_monday():
	with patch('app.services.monday.client.get_items') as mock_monday:
		# Create a fake Item instance with desired attributes
		monday_item = MagicMock(spec=Item)
		monday_item.id = product_id
		monday_item.column_values = {
			'numbers': MagicMock(value=str(product_data['price'])),
			'name': MagicMock(value=product_data['name'])
		}

		# Configure the mock to return a list containing the fake Item
		mock_monday.return_value = [monday_item]
		yield mock_monday


# This is the test for the cache hit scenario
def test_product_data_with_cache_hit(mock_cache):
	product = ProductModel(product_id)
	assert product.data == product_data
	mock_cache.get.assert_called_once_with(f"product:{product_id}")
	mock_cache.set.assert_not_called()  # The cache hit, no need to set again


# If you want to add a test for a cache miss scenario, make sure to adjust the `mock_cache.get.return_value` accordingly before constructing the `ProductModel` instance
def test_product_data_with_cache_miss_and_api_hit(mock_cache, mock_monday):
	mock_cache.get.return_value = None  # Now we simulate a cache miss explicitly
	product = ProductModel(product_id)
	assert product.data == product_data
	mock_cache.set.assert_called_once_with(f"product:{product_id}", json.dumps(product_data).encode('utf-8'))
	mock_monday.get_items.assert_called_once_with(ids=[product_id], get_column_values=True)


def test_product_data_with_api_failure(mock_cache):
	mock_cache.get.return_value = None  # simulate a cache miss

	with patch.object(monday_module, 'client', new_callable=MagicMock) as mock_monday:
		mock_monday.get_items.side_effect = monday_module.MondayError('API error')  # simulate an API error

		with pytest.raises(MondayError) as exec_info:
			product = ProductModel(product_id)
			_ = product.data

		assert 'API Error' in str(exec_info.value)
		mock_cache.set.assert_not_called()
