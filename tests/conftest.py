import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_cache():
	with patch('app.models.base.get_redis_connection') as mock_cache:
		mock_instance = MagicMock()
		mock_cache.return_value = mock_instance
		yield mock_instance
