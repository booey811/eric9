from . import client
from .items import BaseItemType
from .boards import cache as boards
from .client import MondayAPIError


def get_api_items(item_ids):
	try:
		raw = client.conn.items.fetch_items_by_id(item_ids)
	except Exception as e:
		raise MondayAPIError(f"Error calling monday API: {e}")

	if raw.get("errors"):
		raise MondayAPIError(f"Error fetching items from Monday: {raw['errors']}")

	return raw["data"]["items"]


def get_board(board_id):
	boards.get_board(board_id)
