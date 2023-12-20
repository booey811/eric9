import json
import pytest
from unittest.mock import patch, MagicMock

from app.models.base import MondayError
from app.models.product import ProductModel
import app.services.monday as monday_module

# Sample data for the mock to return
product_id = '123'
product_data = {'id': product_id, 'price': 100.0, 'name': 'Sample Product'}
cached_product_data = json.dumps(product_data).encode('utf-8')


# This is the test for the cache hit scenario
def test_product_data_with_cache_hit(mock_cache):
	mock_cache.get.return_value = cached_product_data
	product = ProductModel(product_id)
	assert product.data == product_data
	mock_cache.get.assert_called_once_with(f"product:{product_id}")
	mock_cache.set.assert_not_called()  # The cache hit, no need to set again


# If you want to add a test for a cache miss scenario, make sure to adjust the `mock_cache.get.return_value` accordingly before constructing the `ProductModel` instance
def test_product_data_with_cache_miss_and_fetch_data_mock(mock_cache):
	with patch.object(ProductModel, '_fetch_data') as mock_fetch:
		# Configure the mock to return the fake product data
		mock_fetch.return_value = product_data
		# Simulate the model attribute with a mock that has the same properties
		mock_cache.get.return_value = None
		product = ProductModel(product_id)
		# Access the data property, which should fetch data using the mocked 'model' property
		data = product.data

		# Assert that the data matches what we expect to be set by the model mock
		assert data['price'] == product_data['price']
		assert data['name'] == product_data['name']


def test_product_data_with_api_failure(mock_cache):
	mock_cache.get.return_value = None  # simulate a cache miss

	with patch.object(monday_module, 'client', new_callable=MagicMock) as mock_monday:
		mock_monday.get_items.side_effect = monday_module.MondayError('API error')  # simulate an API error

		with pytest.raises(MondayError) as exec_info:
			product = ProductModel(product_id)
			_ = product.data

		assert 'API Error' in str(exec_info.value)
		mock_cache.set.assert_not_called()
