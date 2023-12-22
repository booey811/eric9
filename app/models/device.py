import moncli
from moncli.models import MondayModel
from moncli import types as cols

from .base import BaseEricModel
from .product import ProductModel


class _BaseDeviceModel(MondayModel):
	product_ids = cols.ItemLinkType(id='connect_boards5')


class DeviceModel(BaseEricModel):

	def __init__(self, device_id, moncli_item: moncli.en.Item = None):
		if moncli_item:
			super().__init__(device_id, moncli_item)
		else:
			super().__init__(device_id)

		self._product_ids = None
		self._products = None

	def _fetch_data(self):
		if not self._model:
			self._model = _BaseDeviceModel(self._call_monday())
		cache_data = {
			"id": str(self.id),
			"name": self.model.name,
			"product_ids": self.product_ids
		}
		return cache_data

	@property
	def cache_key(self):
		return f"device:{self.id}"

	@property
	def product_ids(self):
		if self._product_ids is None:
			ids = [str(item) for item in self.model.product_ids]
			self._product_ids = ids
		return self._product_ids

	@property
	def products(self):
		return [ProductModel(_) for _ in self.product_ids]