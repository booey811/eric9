from moncli.models import MondayModel
from moncli import types as column

from .base import BaseEricModel
from ..cache import get_redis_connection
from ..services import monday


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


class ProductModel(BaseEricModel):

	def __init__(self, product_id, moncli_model: _BaseProductModel = None):
		super().__init__(product_id, moncli_model)
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
