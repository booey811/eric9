import json

import moncli
from moncli.models import MondayModel
from moncli import types as column
import redis

from ..services.monday import MondayError

cache = redis.from_url("redis://localhost:6379")


class _BaseProductModel(MondayModel):
	price = column.NumberType(id='numbers')


class ProductModel:

	def __init__(self, product_id):
		self.id = product_id
		self._cache_data = None
		self._model = None

		self._price = None

	@property
	def model(self):
		if self._model is None:
			try:
				monday_item = moncli.client.get_items(ids=[self.id])[0]
			except moncli.MoncliError as e:
				raise MondayError(e)
			except IndexError:
				raise MondayError(f"No Items found with ID '{self.id}'")
			self._model = _BaseProductModel(monday_item)
		return self._model

	@property
	def price(self):
		if self._price is None:
			cached_data = cache.get(f"product:{self.id}")
			if cached_data:
				price = cached_data['price']
			else:
				price = self.model.price
			self._price = price
		return self._price

	def serialise_for_cache(self):
		data = {
			"id": str(self.id),
			"price": self.model.price,
		}
		return json.dumps(data)