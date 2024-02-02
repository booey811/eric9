import logging

import moncli
from moncli.models import MondayModel
from moncli import types as cols

from .base import BaseEricCacheModel
from .product import ProductModel
from ..services import monday
from ..cache import get_redis_connection, CacheMiss

log = logging.getLogger('eric')


class _BaseDeviceModel(MondayModel):
	product_ids = cols.ItemLinkType(id='connect_boards5')
	legacy_eric_device_id = cols.TextType(id='text')
	product_index_connect = cols.ItemLinkType(id='connect_boards4')
	device_type = cols.StatusType(id='status9')


class DeviceModel(BaseEricCacheModel):
	MONCLI_MODEL = _BaseDeviceModel

	@classmethod
	def query_all(cls):
		device_keys = get_redis_connection().keys("device:*")
		device_ids = [_.decode('utf-8').split(":")[1] for _ in device_keys]
		return [cls(device_id) for device_id in device_ids]

	def __init__(self, device_id, moncli_item: moncli.en.Item = None):
		if moncli_item:
			super().__init__(device_id, moncli_item)
		else:
			super().__init__(device_id)

		self._product_ids = None
		self._products = None
		self._device_type = None

	def __str__(self):
		return f"DeviceModel({self.id}): {self._name or 'Not Fetched'}"

	def prepare_cache_data(self):
		return {
			"name": self.name,
			"product_ids": self.product_ids,
			"device_type": self.model.device_type
		}

	def get_from_cache(self):
		data = super().get_from_cache()
		self._name = data['name']
		self._device_type = data['device_type']
		self._product_ids = data['product_ids']
		return data

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
		if self._products is None:
			items = monday.get_items(self.product_ids)
			self._products = [ProductModel(_.id, _) for _ in items]
		return self._products

	@property
	def device_type(self):
		if self._device_type is None:
			try:
				self.get_from_cache()
			except CacheMiss:
				self._device_type = self.model.device_type
		return self._device_type

	def connect_to_product_group(self):
		if not self.model.legacy_eric_device_id or self.model.legacy_eric_device_id == "new_group77067":  # index Group ID:
			log.debug(f"Correcting legacy ID for {self.model.name}: {self.model.legacy_eric_device_id}")
			if self.products:
				prod = self.products[0]
				device_group_id = prod.model.item.get_group().id
				if device_group_id == "new_group77067":  # index Group ID
					prod = self.products[1]
					device_group_id = prod.model.item.get_group().id
				self.model.legacy_eric_device_id = device_group_id
				for p in self.products:
					if not p.model.legacy_eric_device_id or p.model.legacy_eric_device_id == "new_group77067":  # index Group ID
						p.model.legacy_eric_device_id = device_group_id
						p.model.save()
				self.model.save()
		else:
			return True
