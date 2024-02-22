import json

from ..api.items import BaseItemType, BaseCacheableItem
from ..api import columns
from .product import ProductItem
from ....utilities import notify_admins_of_error
from ....cache import get_redis_connection


class DeviceItem(BaseCacheableItem):

	BOARD_ID = 3923707691

	def __init__(self, item_id=None, api_data: dict | None = None):
		self.device_type = columns.StatusValue('status9')
		self.products_connect = columns.ConnectBoards('connect_boards5')

		self._products = None

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
			"device_type": self.device_type.value,
			"product_ids": [str(_.id) for _ in self.products]
		}

	def load_from_cache(self, cache_data=None):
		if cache_data is None:
			cache_data = self.fetch_cache_data()
		self.name = cache_data['name']
		self.id = cache_data['id']
		self.device_type.value = cache_data['device_type']
		self.products_connect.value = cache_data['product_ids']
		return self

	@property
	def products(self):
		if self._products is None:
			product_ids = self.products_connect.value
			if not product_ids:
				self._products = []
			else:
				self._products = ProductItem.get(product_ids)
		return self._products






