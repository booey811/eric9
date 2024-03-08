from typing import Type

from .....utilities import notify_admins_of_error
from .base import CorporateRepairItem


def get_corporate_repair_class_by_board_id(board_id) -> Type[CorporateRepairItem] or None:
	"""Get the corporate repair class for a ticket"""
	for cls in CorporateRepairItem.__subclasses__():
		if int(cls.BOARD_ID) == int(board_id):
			return cls
	notify_admins_of_error(f"No Corporate Repair Item class found for board_id {board_id}")
	return None
