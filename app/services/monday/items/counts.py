from ..api.items import BaseItemType, MondayDataError
from ..api import columns, monday_connection, get_api_items
from .. import items


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

		self.adjustment_status = columns.StatusValue("status1")

		super().__init__(item_id, api_data, search, cache_data)


class SupplierItem(BaseItemType):

	BOARD_ID = 6390037479

	def __init__(self, item_id=None, api_data: dict = None, search=False, cache_data=None):

		self.parts_connect = columns.ConnectBoards("board_relation3")
		self.order_connect = columns.ConnectBoards("connect_boards0")

		self._current_order = None

		super().__init__(item_id, api_data, search, cache_data)

	def create_new_order_item(self):
		blank = OrderItem()
		blank.supplier_connect = [int(self.id)]
		order = blank.create(self.name)
		self.order_connect = [int(order.id)]
		self.commit()
		self._current_order = OrderItem(order.id).load_from_api()
		return self._current_order

	@property
	def current_order(self):
		if not self._current_order:
			if not self.order_connect.value:
				self._current_order = self.create_new_order_item()
			else:
				order = OrderItem(self.order_connect.value[0]).load_from_api()
				if order.order_status.value != 'Building':
					self.create_new_order_item()
		return self._current_order


class OrderItem(BaseItemType):

	BOARD_ID = 6392094556

	def __init__(self, item_id=None, api_data: dict = None, search=False, cache_data=None):

		self.order_status = columns.StatusValue('status2')
		self.supplier_connect = columns.ConnectBoards('link_to_suppliers')
		self.subitems = columns.ConnectBoards('subitems')

		self._subitem_data = []

		super().__init__(item_id, api_data, search, cache_data)

	def get_line_items(self):
		if not self._subitem_data:
			subitem_ids = self.subitems.value
			if subitem_ids:
				self._subitem_data = get_api_items(subitem_ids)
			else:
				self._subitem_data = []
		return [OrderLineItem(_['id'], _).load_from_api() for _ in self._subitem_data]

	def add_part_to_order(self, part: "items.PartItem"):
		blank = OrderLineItem()
		blank.part_id = str(part.id)
		blank.current_stock_level = int(part.stock_level.value)
		res = monday_connection.items.create_subitem(
			self.id,
			part.name,
			column_values=blank.staged_changes
		)
		# reset subitem data in case we want to view the added lines again (refreshes the list)
		self._subitem_data = []
		return res


class OrderLineItem(BaseItemType):

	BOARD_ID = 6392131341

	def __init__(self, item_id=None, api_data: dict = None, search=False, cache_data=None):

		self.part_id = columns.TextValue("text")
		self.current_stock_level = columns.NumberValue("numbers")

		super().__init__(item_id, api_data, search, cache_data)