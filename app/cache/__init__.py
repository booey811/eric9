import logging

from .redis_client import get_redis_connection
from .. import EricError

log = logging.getLogger('eric')


class CacheMiss(EricError):

	def __init__(self, cache_key, result):
		self.key = cache_key
		self.result = result

	def __str__(self):
		return f"CacheMISS: {self.key}; got {self.result}"
