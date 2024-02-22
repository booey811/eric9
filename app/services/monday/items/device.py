import json

from ..api.items import BaseItemType, BaseCacheableItem
from ..api import columns
from ....utilities import notify_admins_of_error
from ....cache import get_redis_connection


class DeviceItem(BaseCacheableItem):

	BOARD_ID = 3923707691

	def __init__(self, item_id=None, api_data: dict | None = None):
		self.device_type = columns.StatusValue('status9')

		super().__init__(item_id, api_data)

	@classmethod
	def fetch_all(cls, *args):
		return super().fetch_all("device:")

	def cache_key(self):
		return f"device:{self.id}"

	def prepare_cache_data(self):
		return {
			"name": self.name,
			"id": self.id,
		}

	def load_from_cache(self, cache_data=None):
		if cache_data is None:
			cache_data = self.fetch_cache_data()
		self.name = cache_data['name']
		self.id = cache_data['id']
		return cache_data





