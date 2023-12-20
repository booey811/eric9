import json
import abc

import moncli

from ..services.monday import MondayError, client as monday
from ..cache import get_redis_connection


class BaseEricModel(abc.ABC):

	def __init__(self, item_id):
		self.id = str(item_id)

		self._data = None
		self._model = None
		self._cache_key = None
		self._name = None

	def _call_monday(self):
		try:
			return monday.get_items(ids=[self.id], get_column_values=True)[0]
		except moncli.MoncliError as e:
			raise MondayError(e)
		except IndexError:
			raise MondayError(f"No Items found with ID '{self.id}'")

	@property
	def data(self):
		if not self._data:
			cached = self.get_from_cache()
			if cached is not None:
				self._data = json.loads(cached)
			else:
				self._data = self._fetch_data()
				self.save_to_cache()
		return self._data

	def get_from_cache(self):
		cache = get_redis_connection().get(self._cache_key)
		return cache

	def save_to_cache(self):
		# Implement saving to cache
		get_redis_connection().set(
			self._cache_key,
			json.dumps(self._data)
		)

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

	@abc.abstractmethod
	def _fetch_data(self):
		# This method should be implemented in subclasses to fetch data
		pass
