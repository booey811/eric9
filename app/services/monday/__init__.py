import logging
import json
from functools import wraps
import time

from flask import request, jsonify
import moncli

from ...errors import EricError
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


def get_group_items(board_id: int, group_id: str):

	# get repair group
	before_board = time.time()
	main_board = client.get_boards('id', 'groups.[id, title]', ids=[board_id], groups={'ids': [group_id]})[0]
	after_board = time.time()
	log.debug(f'Got Board in {before_board - after_board} seconds')
	group = main_board.get_group(id=group_id)
	after_group = time.time()
	log.debug(f'Got Group in {after_board - after_group} seconds')

	# get repair group items
	simple_item_data = group.get_items(get_column_values=False)
	after_simple = time.time()
	log.debug(f"Got {len(simple_item_data)} simple items in {after_group - after_simple}")
	items = get_items(item_ids=[str(item.id) for item in simple_item_data], column_values=True)
	log.debug(f'Got {len(items)} full items in {after_simple - time.time()} seconds')

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
