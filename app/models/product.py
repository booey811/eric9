import json

import moncli
from moncli.models import MondayModel
from moncli import types as column
import redis

from ..services.monday import MondayError
from ..redis_client import get_redis_connection

cache = get_redis_connection()


class _BaseProductModel(MondayModel):
	price = column.NumberType(id='numbers')


class ProductModel:

	def __init__(self, product_id):
		self.id = str(product_id)
		self._cache_data = None
		self._model = None

		self._price = None

	@property
	def model(self):
		if self._model is None:
			self._model = _BaseProductModel(self._fetch_data())
		return self._model

	@property
	def price(self):
		if self._price is None:
			cached_data = json.loads(cache.get(f"product:{self.id}"))
			if cached_data:
				price = cached_data['price']
			else:
				price = self.model.price
			self._price = price
		return self._price

	def _fetch_data(self):
		try:
			monday_item = moncli.client.get_items(ids=[self.id], get_column_values=True)[0]
		except moncli.MoncliError as e:
			raise MondayError(e)
		except IndexError:
			raise MondayError(f"No Items found with ID '{self.id}'")
		return monday_item
