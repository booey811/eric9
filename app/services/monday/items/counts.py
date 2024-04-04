from ..api.items import BaseItemType
from ..api import columns


class CountItem(BaseItemType):

	BOARD_ID = 2885477229

	def __init__(self, item_id=None, api_data: dict = None, search=False, cache_data=None):

		self.app_meta = columns.LongTextValue("long_text")
		self.view_data = columns.LongTextValue("long_text6")
		self.count_status = columns.StatusValue("status")

		self.subitem_ids = columns.ConnectBoards("subitems")

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


class SupplierItem(BaseItemType):

	BOARD_ID = 6390037479

	def __init__(self, item_id=None, api_data: dict = None, search=False, cache_data=None):

		self.parts_connect = columns.ConnectBoards("board_relation3")
		self.order_connect = columns.ConnectBoards("connect_boards")

		super().__init__(item_id, api_data, search, cache_data)

	def crete_new_order_item(self):
		pass

	def get_current_order_item(self):
		pass


class OrderItem(BaseItemType):

	BOARD_ID = 6392094556

	def __init__(self, item_id=None, api_data: dict = None, search=False, cache_data=None):

		self.order_status = columns.StatusValue('status2')
		self.subitems = columns.ConnectBoards('subtasks')

		super().__init__(item_id, api_data, search, cache_data)

	def get_line_items(self):
		pass


class OrderLineItem(BaseItemType):

	BOARD_ID = 6392131341

	def __init__(self, item_id=None, api_data: dict = None, search=False, cache_data=None):

		self.part_id = columns.TextValue("text")
		self.current_stock_level = columns.NumberValue("numbers")

		super().__init__(item_id, api_data, search, cache_data)