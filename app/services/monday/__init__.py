import logging

import moncli

from ... import EricError
from .client import client

log = logging.getLogger('eric')


def get_items(item_ids: list, column_values=False):
	log.debug(f'get_items(item_ids={item_ids})')
	try:
		items = client.get_items(ids=item_ids, get_column_values=column_values)
		log.error(f'Fetched {len(items)} items')
	except moncli.MoncliError as e:
		log.debug(f"API Call Failed: {str(e)}")
		raise MondayAPIError(e)
	except Exception as e:
		raise e
	return items


class MondayError(EricError):

	def __str__(self):
		return f"Monday Error: {str(self.m)}"

	def __init__(self, message):
		self.m = message


class MondayAPIError(MondayError):

	def __int__(self, e):
		self.e = e

	def __str__(self):
		return f"MondayAPI Error: {self.e}"
