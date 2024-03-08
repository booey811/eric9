from ...api import columns
from .base import CorporateRepairItem, CorporateAccountItem


class VCCPRepairItem(CorporateRepairItem):
	BOARD_ID = 6220721677
	"""The board id for the VCCP board"""

	@property
	def account_item(self) -> CorporateAccountItem:
		"""Get the corporate account item associated with this repair item"""
		return CorporateAccountItem(1985130305)

	@staticmethod
	def get_column_id_map():
		"""Get the column id map for this item"""
		return {
			"ticket_id": columns.TextValue("text4"),
			"imeisn": columns.TextValue("text"),
			"device_name": columns.TextValue("text9"),
			"description": columns.LongTextValue("long_text"),
			"cost": columns.NumberValue("numbers"),
			"main_board_connect": columns.ConnectBoards("connect_boards")
		}
