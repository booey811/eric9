import json

import moncli
from moncli.models import MondayModel
from moncli import types as column

from ..services.monday import MondayError, client as monday
from ..redis_client import get_redis_connection


class _BaseProductModel(MondayModel):
	price = column.NumberType(id='numbers')


class ProductModel:

	def __init__(self, product_id):
		self.id = str(product_id)
		self._data = None
		self._model = None

		self._name = None
		self._price = None

	@property
	def data(self):
		if not self._data:
			cached = self._data = get_redis_connection().get(f"product:{self.id}")
			if not cached:
				data = self._fetch_data()
				get_redis_connection().set(
					f"product:{self.id}",
					json.dumps(data)
				)
			else:
				data = json.loads(cached)
			self._data = data
		return self._data

	def _fetch_data(self):
		try:
			monday_item = monday.get_items(ids=[self.id], get_column_values=True)[0]
		except moncli.MoncliError as e:
			raise MondayError(e)
		except IndexError:
			raise MondayError(f"No Items found with ID '{self.id}'")
		self._model = _BaseProductModel(monday_item)
		cache_data = {
			"id": str(self.id),
			"price": self.price,
			"name": self.model.name
		}
		return cache_data

	@property
	def model(self):
		if self._model is None:
			self._fetch_data()
		return self._model

	@property
	def name(self):
		if self._name is None:
			self._name = self.data['name']
		return self._name

	@property
	def price(self):
		if self._price is None:
			self._price = self.data['price']
		return self._price

