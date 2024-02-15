from ..api.items import BaseItemType, BaseCacheableItem
from ..api import columns


class DeviceItem(BaseCacheableItem):

	BOARD_ID = 3923707691

	def cache_key(self):
		return f"device:{self.id}"

	def prepare_cache_data(self):
		return {
			"name": self.name,
			"id": self.id,
		}

	def load_from_cache(self):
		cache_data = self.fetch_cache_data()
		self.name = cache_data['name']
		self.id = cache_data['id']
		return cache_data





