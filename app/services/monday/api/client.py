import os

import monday

import config

from .exceptions import MondayAPIError

conf = config.get_config()

conn = monday.MondayClient(conf.MONDAY_KEYS["gabe"])


def get_api_items(item_ids):
	item_ids = [int(_) for _ in item_ids]
	if not item_ids:
		return []
	try:
		raw = conn.items.fetch_items_by_id(ids=item_ids)
	except Exception as e:
		raise MondayAPIError(f"Error calling monday API: {e}")

	if raw.get("error_message"):
		raise MondayAPIError(f"Error fetching items from Monday: {raw['error_message']}")

	return raw["data"]["items"]


def get_api_items_by_group(board_id, group_id):
	try:
		raw = conn.groups.get_items_by_group(board_id, group_id)
	except Exception as e:
		raise MondayAPIError(f"Error calling monday API: {e}")

	if raw.get("error_message"):
		raise MondayAPIError(f"Error fetching items from Monday: {raw['errors']}")

	return raw["data"]["boards"][0]["groups"][0]["items_page"]["items"]
