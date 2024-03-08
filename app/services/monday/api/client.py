import os

import monday

import config

from .exceptions import MondayAPIError

conf = config.get_config()

conn = monday.MondayClient(conf.MONDAY_KEYS["gabe"])


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
	try:
		raw = conn.groups.get_items_by_group(board_id, group_id)
	except Exception as e:
		raise MondayAPIError(f"Error calling monday API: {e}")

	if raw.get("error_message"):
		raise MondayAPIError(f"Error fetching items from Monday: {raw['errors']}")

	return raw["data"]["boards"][0]["groups"][0]["items_page"]["items"]
