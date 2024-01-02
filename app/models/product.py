from moncli.models import MondayModel
from moncli import types as column
import moncli

from .base import BaseEricModel
from ..cache import get_redis_connection
from ..services import monday
from .. import EricError


def get_products(product_ids: list):
	results = []
	keys = [f"product:{_}" for _ in product_ids]
	cache_results = get_redis_connection().mget(keys)
	missed = []

	for p_id, result in zip(product_ids, cache_results):
		if not result:
			missed.append(p_id)
		else:
			results.append(ProductModel(p_id))

	if missed:
		moncli_results = monday.client.get_items(ids=missed, get_column_values=True)
		for mon in moncli_results:
			results.append(ProductModel(mon.id, mon))

	return results


class _BaseProductModel(MondayModel):
	price = column.NumberType(id='numbers')
	device_id = column.ItemLinkType(id='link_to_devices6')


class ProductModel(BaseEricModel):

	def __init__(self, product_id, moncli_item: moncli.en.Item = None):
		if moncli_item:
			super().__init__(product_id, _BaseProductModel(moncli_item))
		else:
			super().__init__(product_id)

		self._price = None
		self._device_id = None

	def _fetch_data(self):
		if not self._model:
			self._model = _BaseProductModel(self._call_monday())
		cache_data = {
			"id": str(self.id),
			"price": self.model.price,
			"name": self.model.name,
			"device_id": str(self.model.device_id)
		}
		return cache_data

	@property
	def cache_key(self):
		return f"product:{self.id}"

	@property
	def price(self):
		if self._price is None:
			self._price = self.data['price']
			if self._price is None:
				raise MissingProductData(self.id, "Price")
		return self._price

	@property
	def device_id(self):
		if self._device_id is None:
			self._device_id = self.data['device_id']
			if self._device_id is None:
				raise MissingProductData(self.id, "Device ID")
		return self._device_id


class MissingProductData(EricError):

	def __init__(self, product_id, missing_data_name):
		self.p_id = product_id
		self.missing_field = missing_data_name

	def __str__(self):
		return f"Product({self.p_id}) missing '{self.missing_field}' field"
