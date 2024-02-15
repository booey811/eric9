from ..api.items import BaseItemType, BaseCacheableItem
from ..api import columns
from ..api.exceptions import MondayDataError
from .... import notify_admins_of_error


class ProductItem(BaseCacheableItem):
	BOARD_ID = 2477699024

	device_connect = columns.ConnectBoards("link_to_devices6")
	parts_connect = columns.ConnectBoards("connect_boards8")

	price = columns.NumberValue("numbers")

	required_minutes = columns.NumberValue("numbers7")
	woo_commerce_product_id = columns.TextValue("text3")

	def cache_key(self):
		return f"product:{self.id}"

	def load_from_cache(self):
		cache_data = self.fetch_cache_data()
		self.price.value = int(cache_data['price'])
		self.required_minutes.value = int(cache_data['required_minutes'])
		self.name = cache_data['name']
		return cache_data

	def prepare_cache_data(self):
		data = {
			"price": self.price.value,
			"required_minutes": self.required_minutes.value,
			"name": self.name,
			"device_id": self.device_id
		}

		if not data['device_id']:
			raise MondayDataError(f"Device ID not set for product {self.id}")

		return data

	@property
	def device_id(self):
		if self.device_connect.value:
			return self.device_connect.value[0]
		else:
			notify_admins_of_error(f"{str(self)} has no device connection")
			return None

	@device_id.setter
	def device_id(self, value):
		self.device_connect = [int(value)]
