from moncli.models import MondayModel
from moncli import types as column

from .base import BaseEricModel


class _BaseProductModel(MondayModel):
	price = column.NumberType(id='numbers')


class ProductModel(BaseEricModel):

	def __init__(self, product_id):
		super().__init__(product_id)
		self._cache_key = f"product:{self.id}"

		self._price = None

	def _fetch_data(self):
		self._model = _BaseProductModel(self._call_monday())
		cache_data = {
			"id": str(self.id),
			"price": self.price,
			"name": self.model.name
		}
		return cache_data

	@property
	def price(self):
		if self._price is None:
			self._price = self.data['price']
		return self._price
