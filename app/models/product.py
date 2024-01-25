import logging

from moncli.models import MondayModel
from moncli import types as column
import moncli

from .base import BaseEricModel, BaseEricCacheModel
from ..cache import get_redis_connection, CacheMiss
from ..services import monday
from .. import EricError, DataError

log = logging.getLogger('eric')


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
			super().model
		self._name = self._model.name
		self._price = self._model.price
		try:
			self._device_id = self._model.device_connect[0]
		except IndexError:
			log.warning(f"{str(self)} has no device connection")
			self._device_id = None
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
		if self._price is None:
			try:
				self.get_from_cache()
			except CacheMiss:
				self.model
		return self._price

	@property
	def device_id(self):
		if self._device_id is None:
			try:
				self.get_from_cache()
			except CacheMiss:
				self.model
		return self._device_id


class MissingProductData(EricError):

	def __init__(self, item_id, missing_attribute):
		self.item_id = item_id
		self.att = missing_attribute

	def __str__(self):
		return f"Product({self.item_id}) Missing Data {self.att}"
