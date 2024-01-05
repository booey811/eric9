import json
import pytest
from unittest.mock import Mock, patch

from app.models.base import BaseEricCacheModel, CacheMiss


# Create a subclass of the abstract BaseEricCacheModel for testing purposes
class TestModel(BaseEricCacheModel):
	def prepare_cache_data(self):
		return {'name': 'Test Name'}

	@property
	def cache_key(self) -> str:
		return f"test_model:{self.id}"


# Fixture to mock Redis connection and get_items function
@pytest.fixture
def mock_redis_items():
	with patch('app.models.base.get_redis_connection') as mock_redis, \
			patch('app.models.base.get_items') as mock_get_items:
		mock_redis.return_value.get.return_value = None  # simulate cache miss
		mock_get_items.return_value = [Mock()]  # mock list with a single moncli item
		yield mock_redis, mock_get_items


def test_moncli_item(mock_redis_items):
	mock_redis, mock_get_items = mock_redis_items

	test_model = TestModel(item_id=123)

	# Test that the moncli_item property fetches the item
	item = test_model.moncli_item
	assert item is not None
	mock_get_items.assert_called_once()


def test_get_from_cache_hit(mock_redis_items):
	mock_redis, _ = mock_redis_items
	mock_redis.return_value.get.return_value = json.dumps({'name': 'Test Name'})

	test_model = TestModel(item_id=123)

	# Test cache hit
	data = test_model.get_from_cache()
	assert data == {'name': 'Test Name'}


def test_get_from_cache_miss(mock_redis_items):
	mock_redis, _ = mock_redis_items
	mock_redis.return_value.get.return_value = None  # simulate cache miss

	test_model = TestModel(item_id=123)

	# Test cache miss exception
	with pytest.raises(CacheMiss):
		test_model.get_from_cache()
