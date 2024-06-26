import os
import logging

import monday

import config

from .exceptions import MondayAPIError

conf = config.get_config()

conn = monday.MondayClient(conf.MONDAY_KEYS["system"])

log = logging.getLogger('eric')


def get_api_items(item_ids):
	item_data = []
	item_ids = [int(_) for _ in item_ids]
	if not item_ids:
		return []

	# Slice item_ids into blocks of 25
	item_id_blocks = [item_ids[i:i + 25] for i in range(0, len(item_ids), 25)]

	for item_id_block in item_id_blocks:
		try:
			query_result = conn.items.fetch_items_by_id(ids=item_id_block)
		except Exception as e:
			raise MondayAPIError(f"Error calling monday API: {e}")

		if query_result.get("error_message"):
			raise MondayAPIError(f"Error fetching items from Monday: {query_result['error_message']}")

		item_data.extend(query_result["data"]["items"])

	return item_data


def get_api_items_by_group(board_id, group_id):
	results = []
	try:
		raw = conn.groups.get_items_by_group(board_id, group_id)
	except Exception as e:
		raise MondayAPIError(f"Error calling monday API: {e}")

	if raw.get("error_message"):
		raise MondayAPIError(f"Error fetching items from Monday: {raw['errors']}")

	api_data = raw["data"]["boards"][0]["groups"][0]["items_page"]
	results.extend(api_data["items"])

	while api_data.get('cursor'):
		raw = conn.groups.get_items_by_group(board_id, group_id, cursor=api_data['cursor'])
		if raw.get("error_message"):
			raise MondayAPIError(f"Error fetching items from Monday: {raw['errors']}")
		api_data = raw["data"]["boards"][0]["groups"][0]["items_page"]
		results.extend(api_data["items"])

	return results


def get_items_by_board_id(board_id):

	item_data = []
	try:
		query_results = conn.boards.fetch_items_by_board_id(
			int(board_id)
		)['data']['boards'][0]['items_page']
		cursor = query_results.get('cursor')
		log.debug(f"Cursor: {cursor}, {len(query_results['items'])} items fetched")
		counter = len(query_results['items'])
		item_data.extend(query_results['items'])
		while cursor:
			query_results = conn.boards.fetch_items_by_board_id(
				int(board_id),
				cursor=cursor
			)['data']['boards'][0]['items_page']
			cursor = query_results.get('cursor')
			log.debug(f"Cursor: {cursor}, {len(query_results['items'])} items fetched")
			counter += len(query_results['items'])
			item_data.extend(query_results['items'])
			log.debug(f"Total items fetched: {counter}")
	except Exception as e:
		raise MondayAPIError(f"Error fetching items by board: {e}")
	return item_data
