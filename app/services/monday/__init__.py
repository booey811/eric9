import logging
import json
from functools import wraps

from flask import request, jsonify
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


def monday_challenge(func):
	@wraps(func)
	def decorated_function(*args, **kwargs):
		# Check if the incoming request has a 'challenge' key
		challenge = request.json.get('challenge') if request.json else None
		if challenge:
			# If it's a challenge, return the challenge code back to monday.com
			return jsonify({'challenge': challenge})
		# Otherwise, proceed with the actual processing
		return func(*args, **kwargs)
	return decorated_function


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
