import json
import abc
import logging

import moncli

from ..services.monday import MondayError, get_items
from ..cache import get_redis_connection, CacheMiss

log = logging.getLogger('eric')


class BaseEricModel:
	"""
	A base model class that interacts with monday.com to fetch and cache item data.

	Attributes:
	id (int): The unique identifier of the monday.com item.
	_moncli_item (moncli.en.Item): The moncli item instance.
	_model: The Moncli model instance, populated on-demand.
	"""
	MONCLI_MODEL = None

	def __init__(self, item_id, moncli_item: moncli.en.Item = None):
		self.id = item_id
		self._name = None
		self._moncli_item = moncli_item

		self._model = None

	@property
	def moncli_item(self) -> moncli.en.Item:
		"""
		Fetch and return the moncli item if not already fetched.

		Returns:
		The moncli item instance.

		Raises:
		MondayError: If unable to fetch the item, or more than one item is fetched.
		"""
		if not self._moncli_item:
			log.debug(f"Fetching {str(self)}")
			items = get_items([self.id], column_values=True)
			if not items:
				log.debug('Failure: Failed to fetch any items')
				raise MondayError(f"{str(self)} fetched no items")
			if len(items) != 1:
				log.debug(f'Failure: Fetched {len(items)} items: {[item.id for item in items]}')
				raise MondayError(f"{str(self)} fetched {len(items)} items")
			log.debug("Fetch successful")
			self._moncli_item = items[0]
		return self._moncli_item

	@property
	def model(self) -> type(MONCLI_MODEL):
		"""
		Return the Moncli model for this item, instantiating it if needed.

		Returns:
		An instance of the Moncli model.

		Raises:
		NotImplementedError: If the MONCLI_MODEL attribute is not defined.
		"""
		if self.MONCLI_MODEL is None:
			raise NotImplementedError(
				"MONCLI_MODEL attribute must be set to use the `model` property."
			)
		if not self._model:
			self._model = self.MONCLI_MODEL(self.moncli_item)
		return self._model


class BaseEricCacheModel(BaseEricModel):

	def __init__(self, item_id, moncli_item: moncli.en.Item = None):
		super().__init__(item_id, moncli_item)

		self._cache_key = None

	@property
	@abc.abstractmethod
	def cache_key(self) -> str:
		"""
		Cache key property to be implemented by deriving classes.
		This key is used to store and retrieve the cache data.
		"""
		pass

	@abc.abstractmethod
	def prepare_cache_data(self):
		"""
		Prepare the model's cache data before saving it to the cache.
		This method must be implemented by deriving classes to serve cache data.
		"""
		pass

	def get_from_cache(self):
		log.debug(f"Searching Cache: {str(self)}")
		data = get_redis_connection().get(self.cache_key)
		try:
			data = json.loads(data)
		except json.JSONDecodeError:
			raise CacheMiss(str(self), data)
		except TypeError:
			raise CacheMiss(str(self), data)
		if not data:
			raise CacheMiss(self.cache_key, data)
		log.debug(f"Cache HIT {str(self)}: {data}")
		return data

	def save_to_cache(self):
		"""
		Save the model's data to the cache using the prepared cache data.

		Returns:
		The cache data dictionary that was saved.
		"""
		data = self.prepare_cache_data()
		log.debug(f"Cache SAVE {self}: {data}")
		get_redis_connection().set(
			self.cache_key,
			json.dumps(data)
		)
		return data

	@property
	def name(self):
		if not self._name:
			self.get_from_cache()
		return self._name
