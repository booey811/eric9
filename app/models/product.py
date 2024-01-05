import logging

from moncli.models import MondayModel
from moncli import types as column
import moncli

from .base import BaseEricModel, BaseEricCacheModel
from ..cache import get_redis_connection, CacheMiss
from ..services import monday
from .. import EricError, DataError

log = logging.getLogger('eric')


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
	device_connect = column.ItemLinkType(id='link_to_devices6')


class ProductModel(BaseEricCacheModel):
	MONCLI_MODEL = _BaseProductModel

	def __init__(self, product_id, moncli_item: moncli.en.Item = None):
		super().__init__(product_id, moncli_item)

		self._price = None
		self._device_id = None

	def __str__(self):
		return f"Product({self.id})"

	@property
	def cache_key(self):
		return f"product:{self.id}"

	@property
	def model(self):
		if not self._model:
			model = super().model
			self._name = model.name
			self._price = model.price
			self._device_id = model.device_connect[0]
			self.save_to_cache()
		return self._model

	def get_from_cache(self):
		data = super().get_from_cache()
		self._name = data['name']
		self._price = data['price']
		self._device_id = data['device_id']
		return data

	def prepare_cache_data(self):
		return {
			"price": self.price,
			"name": self.name,
			"device_id": str(self.device_id)
		}

	@property
	def price(self):
		if not self._price:
			self.get_from_cache()
		return self._price

	@property
	def device_id(self):
		if not self._device_id:
			self.get_from_cache()
		return self._device_id


class MissingProductData(EricError):

	def __init__(self, item_id, missing_attribute):
		self.item_id = item_id
		self.att = missing_attribute

	def __str__(self):
		return f"Product({self.item_id}) Missing Data {self.att}"
