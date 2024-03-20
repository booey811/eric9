from ..api.items import BaseItemType
from ..api import columns
from . import MainItem


class SaleControllerItem(BaseItemType):
	BOARD_ID = 6285416596

	def __init__(self, item_id=None, api_data=None, search=None, cache_data=None):
		self.main_item_id = columns.TextValue("text")
		self.main_item_connect = columns.ConnectBoards("connect_boards")

		self.processing_status = columns.StatusValue("status4")

		self.invoicing_status = columns.StatusValue("status1")
		self.invoice_item_id = columns.TextValue("text70")
		self.invoice_item_connect = columns.ConnectBoards("connect_boards9")

		self.subitem_ids = columns.ConnectBoards("subitems")

		super().__init__(item_id, api_data, search, cache_data)

	def create_invoice_item(self, main_item=None) -> "InvoiceControllerItem" or None:
		# create the invoice item

		if self.invoice_item_id.value or self.invoice_item_connect.value:
			# invoice item already exists
			return InvoiceControllerItem(self.invoice_item_id.value)

		if not main_item:
			main_item = MainItem(self.main_item_id.value).load_from_api()

		if main_item.client.value != "Corporate":
			# Not a corporate sale, no invoice needed
			self.invoicing_status = "Not Corporate"
			self.commit()
			return None

		invoice_item = InvoiceControllerItem()
		invoice_item.sales_item_id = str(self.id)
		invoice_item.sales_item_connect = [int(self.id)]
		invoice_item.main_item_id = str(self.main_item_id.value)
		invoice_item.main_item_connect = [int(self.main_item_id.value)]
		invoice_item.create(self.name)

		self.invoice_item_id = str(invoice_item.id)
		self.invoice_item_connect = [int(invoice_item.id)]
		self.invoicing_status = "Pushed to Invoicing"
		self.commit()

		return invoice_item


class SaleLineItem(BaseItemType):
	BOARD_ID = 6285426254

	def __init__(self, item_id=None, api_data=None, search=None, cache_data=None):
		self.source_id = columns.TextValue("text")
		self.line_type = columns.StatusValue("status2")
		self.price_inc_vat = columns.NumberValue("numbers")

		super().__init__(item_id, api_data, search, cache_data)


class InvoiceControllerItem(BaseItemType):
	BOARD_ID = 6287948446

	def __init__(self, item_id=None, api_data=None, search=None, cache_data=None):
		self.main_item_id = columns.TextValue("text")
		self.main_item_connect = columns.ConnectBoards("connect_boards")

		self.sales_item_id = columns.TextValue("text5")
		self.sales_item_connect = columns.ConnectBoards("connect_boards_1")

		self.processing_status = columns.StatusValue("status4")

		self.generation_status = columns.StatusValue("status1")

		self.subitem_ids = columns.ConnectBoards("subitems")

		super().__init__(item_id, api_data, search, cache_data)


class InvoiceLineItem(BaseItemType):
	BOARD_ID = 6288579132

	def __init__(self, item_id=None, api_data=None, search=None, cache_data=None):
		self.line_type = columns.StatusValue("status27")
		self.price_inc_vat = columns.NumberValue("numbers")
		self.line_item_id = columns.TextValue("text")
		self.line_description = columns.LongTextValue("line_description")

		super().__init__(item_id, api_data, search, cache_data)
