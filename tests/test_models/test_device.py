import json

import pytest
from pytest_mock import mocker

from app.models.device import DeviceModel
from app.cache import CacheMiss

def test_query_all(mocker):
    # Mock the Redis connection and its `keys` method
    mock_redis = mocker.MagicMock()
    mocker.patch('app.models.device.get_redis_connection', return_value=mock_redis)
    mock_redis.keys.return_value = [b'device:1', b'device:2', b'device:3']

    # Call the `query_all` method
    devices = DeviceModel.query_all()

    # Assert that the `keys` method was called with the correct pattern
    mock_redis.keys.assert_called_once_with('device:*')

    # Assert that the method returned the correct devices
    assert len(devices) == 3
    assert [device.id for device in devices] == ['1', '2', '3']



def test_query_all_returns_correct_devices_when_cache_has_devices(mocker):
    mock_redis = mocker.MagicMock()
    mocker.patch('app.models.device.get_redis_connection', return_value=mock_redis)
    mock_redis.keys.return_value = [b'device:1', b'device:2', b'device:3']

    devices = DeviceModel.query_all()

    assert len(devices) == 3
    assert [device.id for device in devices] == ['1', '2', '3']


def test_query_all_returns_empty_list_when_cache_has_no_devices(mocker):
    mock_redis = mocker.MagicMock()
    mocker.patch('app.models.device.get_redis_connection', return_value=mock_redis)
    mock_redis.keys.return_value = []

    devices = DeviceModel.query_all()

    assert devices == []


def test_device_model_initialization_with_moncli_item(mocker):
    mock_item = mocker.MagicMock()
    device = DeviceModel('1', mock_item)

    assert device.id == '1'
    assert device._moncli_item == mock_item


def test_device_model_initialization_without_moncli_item(mocker):
    device = DeviceModel('1')

    assert device.id == '1'
    assert device._moncli_item is None


def test_get_from_cache_returns_correct_data(mocker):
    mock_redis = mocker.MagicMock()
    mocker.patch('app.models.base.get_redis_connection', return_value=mock_redis)
    mock_redis.get.return_value = json.dumps({
        "name": "Device 1",
        "product_ids": ['1', '2', '3'],
        "device_type": "Type 1"
    })

    device = DeviceModel('1')
    data = device.get_from_cache()

    assert data == {
        "name": "Device 1",
        "product_ids": ['1', '2', '3'],
        "device_type": "Type 1"
    }


def test_get_from_cache_raises_exception_when_no_data_in_cache(mocker):
    mock_redis = mocker.MagicMock()
    mocker.patch('app.models.device.get_redis_connection', return_value=mock_redis)
    mock_redis.get.return_value = None

    device = DeviceModel('1')

    with pytest.raises(CacheMiss):
        device.get_from_cache()