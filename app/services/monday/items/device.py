import json

from ..api.items import BaseItemType, BaseCacheableItem
from ..api import columns, exceptions
from .. import items
from .product import ProductItem
from ....utilities import notify_admins_of_error
from ....cache import get_redis_connection


class DeviceItem(BaseCacheableItem):
	BOARD_ID = 3923707691

	def __init__(self, item_id=None, api_data: dict | None = None):
		self.device_type = columns.StatusValue('status9')
		self.products_connect = columns.ConnectBoards('connect_boards5')
		self.pre_checks_connect = columns.ConnectBoards('connect_boards41')

		self._products = None
		self._pre_check_set = None

		super().__init__(item_id, api_data)

	@classmethod
	def fetch_all(cls, slack_data=False, force_api=False, *args):
		results = super().fetch_all("device:", force_api=force_api)
		if not slack_data:
			return results
		else:
			dct = {}
			for device in results:
				inner_list = [device.name, str(device.id)]
				try:
					dct[device.device_type.value].append(inner_list)
				except KeyError:
					dct[device.device_type.value] = [inner_list]
			return dct

	def cache_key(self):
		return f"device:{self.id}"

	def prepare_cache_data(self):
		return {
			"name": self.name,
			"id": self.id,
			"device_type": self.device_type.value,
			"product_ids": [str(_) for _ in self.products_connect.value],
			"pre_check_set_id": [self.pre_checks_connect.value[0]] if self.pre_checks_connect.value else []
		}

	def load_from_cache(self, cache_data=None):
		if cache_data is None:
			cache_data = self.fetch_cache_data()
		self.name = cache_data['name']
		self.id = cache_data['id']
		self.device_type.value = cache_data['device_type']
		self.products_connect.value = cache_data['product_ids']
		try:
			self.pre_checks_connect.value = cache_data['pre_check_set_id']
		except KeyError:
			self.load_from_api()
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

	@property
	def pre_check_set(self) -> items.misc.PreCheckSet | None:
		if self._pre_check_set is None:
			if not self.pre_checks_connect.value:
				if not self._api_data:
					self.load_from_api()
				if self.pre_checks_connect.value:
					self._pre_check_set = items.misc.PreCheckSet(self.pre_checks_connect.value[0])
			else:
				self._pre_check_set = items.misc.PreCheckSet(self.pre_checks_connect.value[0])
		if self._pre_check_set is None:
			raise exceptions.MondayDataError(f"Device {self.id} has no pre-check set attached")
		return self._pre_check_set
