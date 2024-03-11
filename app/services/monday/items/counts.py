from ..api.items import BaseItemType
from ..api import columns


class CountItem(BaseItemType):

	BOARD_ID = 2885477229

	def __init__(self, item_id=None, api_data: dict = None, search=False, cache_data=None):

		self.app_meta = columns.LongTextValue("long_text")
		self.view_data = columns.LongTextValue("long_text6")
		self.count_status = columns.StatusValue("status")

		super().__init__(item_id, api_data, search, cache_data)


class CountLineItem(BaseItemType):

	BOARD_ID = 2885485385

	def __init__(self, item_id=None, api_data: dict = None, search=False, cache_data=None):

		self.part_id = columns.TextValue("text")

		self.counted = columns.NumberValue("numbers")
		self.expected = columns.NumberValue("numbers2")
		self.supply_price = columns.NumberValue("numbers1")

		self.adjustment_status = columns.StatusValue("status1")

		super().__init__(item_id, api_data, search, cache_data)