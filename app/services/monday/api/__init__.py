from . import client
from .items import BaseItemType
from .boards import cache as boards
from .client import MondayAPIError


def get_api_items(item_ids):
	item_ids = [int(_) for _ in item_ids]
	try:
		raw = client.conn.items.fetch_items_by_id(ids=item_ids)
	except Exception as e:
		raise MondayAPIError(f"Error calling monday API: {e}")

	if raw.get("error_message"):
		raise MondayAPIError(f"Error fetching items from Monday: {raw['errors']}")

	return raw["data"]["items"]


def get_board(board_id):
	boards.get_board(board_id)


def get_api_items_by_group(board_id, group_id):
	try:
		raw = client.conn.groups.get_items_by_group(board_id, group_id)
	except Exception as e:
		raise MondayAPIError(f"Error calling monday API: {e}")

	if raw.get("error_message"):
		raise MondayAPIError(f"Error fetching items from Monday: {raw['errors']}")

	return raw["data"]["boards"][0]["groups"][0]["items_page"]["items"]
