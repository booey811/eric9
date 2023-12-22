import json
import abc
import logging

import moncli

from ..services.monday import MondayError, client as monday
from ..cache import get_redis_connection

log = logging.getLogger('eric')


class BaseEricModel(abc.ABC):

	def __init__(self, item_id, moncli_model=None):
		self.id = str(item_id)

		self._data = None
		self._model = moncli_model
		self._cache_key = None
		self._name = None

		log.debug(f"Created {self}")

	def __str__(self):
		return f"BaseEricModel({self.id})"

	def _call_monday(self):
		try:
			log.debug(f"Calling monday.get_items({self.id})")
			return monday.get_items(ids=[self.id], get_column_values=True)[0]
		except moncli.MoncliError as e:
			raise MondayError(e)
		except IndexError:
			raise MondayError(f"No Items found with ID '{self.id}'")

	@property
	def data(self):
		if not self._data:
			log.debug(f"{str(self)} missing data")
			cached = self.get_from_cache()
			if cached is not None:
				self._data = json.loads(cached)
			else:
				self._data = self._fetch_data()
				self.save_to_cache()
		return self._data

	def get_from_cache(self):
		log.debug(f"Fetching from cache: {str(self)}")
		cache = get_redis_connection().get(self.cache_key)
		if cache == 'null' or cache is None:
			log.debug("Cache: MISS")
			return None
		else:
			log.debug('Cache: HIT')
			log.debug(cache)
			return cache

	def save_to_cache(self):
		# Implement saving to cache
		log.debug("Cache: SAVE")
		log.debug(f"{self.cache_key}: {self._data}")
		get_redis_connection().set(
			self.cache_key,
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
		pass

	@abc.abstractmethod
	def cache_key(self):
		pass
