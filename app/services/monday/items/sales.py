from ....errors import EricError
from ....utilities import notify_admins_of_error
from ... import zendesk, monday
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
		self.invoice_line_item_id = columns.TextValue("text018")
		self.invoice_line_item_connect = columns.ConnectBoards("board_relation")

		self.corporate_account_connect = columns.ConnectBoards("connect_boards0")
		self.corporate_account_item_id = columns.TextValue("text00")
		self.price_override = columns.NumberValue("numbers7")

		self.subitem_ids = columns.ConnectBoards("subitems")

		# properties
		self._main_item = None
		self._corporate_account_item = None

		super().__init__(item_id, api_data, search, cache_data)

	def get_main_item(self) -> MainItem:
		if not self._main_item:
			main_id = self.main_item_id.value
			self._main_item = MainItem(main_id).load_from_api()
		return self._main_item

	def get_corporate_account_item(self) -> "monday.items.corporate.base.CorporateAccountItem":
		if not self._corporate_account_item:
			if self.corporate_account_connect.value:
				if not self.corporate_account_item_id.value:
					self.corporate_account_item_id.value = str(self.corporate_account_connect.value[0])
					self.commit()
				i = monday.items.corporate.base.CorporateAccountItem(self.corporate_account_connect.value[0])
			else:
				if not self.get_main_item().ticket_id.value:
					raise InvoiceDataError("No ticket found for sale item, please assign a Corporate Account Link")
				ticket = zendesk.client.tickets(id=int(self.get_main_item().ticket_id.value))
				organization = ticket.organization
				if not organization:
					raise InvoiceDataError("No organization found for ticket, please assign a Corporate Account Link")
				corporate_account_item_id = organization['organization_fields']['monday_corporate_id']
				if not corporate_account_item_id:
					raise InvoiceDataError(f"No corporate account reference found for {organization['name']}, please assign a Corporate Account Link")
				self.corporate_account_item_id.value = str(corporate_account_item_id)
				self.corporate_account_connect.value = [int(corporate_account_item_id)]
				self.commit()
				i = monday.items.corporate.base.CorporateAccountItem(corporate_account_item_id)
			self._corporate_account_item = i
		return self._corporate_account_item




	def add_to_invoice(self):
		main_item = MainItem(self.main_item_id.value)
		try:
			if main_item.client.value == "End User":
				self.invoicing_status = "Not Corporate"
				self.commit()
				return self
			elif main_item.client.value == "Warranty":
				self.invoicing_status = "Warranty"
				self.commit()
				return self
			else:

				device = monday.items.device.DeviceItem(main_item.device_id.value)
				repairs = [monday.items.sales.SaleLineItem(item_id=item_id) for item_id in self.subitem_ids.value]
				repair_total = 0
				repair_description = device.name
				for repair in repairs:
					repair_total += int(repair.price_inc_vat.value)
					repair_description += f'{repair.name.replace(device.name, "")}, '
				repair_description = repair_description[:-2]
		except Exception as e:
			pass






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
		self.sales_item_id = columns.TextValue("text5")
		self.sales_item_connect = columns.ConnectBoards("connect_boards_1")

		self.corporate_account_item_id = columns.TextValue("text9")
		self.corporate_account_connect = columns.ConnectBoards("connect_boards0")

		self.invoice_id = columns.TextValue("text8")
		self.invoice_number = columns.TextValue("text0")

		self.generation_status = columns.StatusValue("status1")
		self.xero_sync_status = columns.StatusValue("status4")

		self.invoice_status = columns.StatusValue("status58")

		self.subitem_ids = columns.ConnectBoards("subitems")

		super().__init__(item_id, api_data, search, cache_data)

	def add_invoice_line(self, item_name, description, total_price, line_type) -> "InvoiceLineItem":
		blank = InvoiceLineItem()
		blank.line_description = description
		blank.price_inc_vat = total_price
		blank.line_type = line_type
		try:
			r = monday.api.monday_connection.items.create_subitem(
				parent_item_id=int(self.id),
				subitem_name=item_name,
				column_values=blank.staged_changes
			)['data']
		except KeyError as e:
			notify_admins_of_error(f"Error creating invoice line item: {e}")
			raise InvoiceDataError(f"Error creating invoice line item on Monday: {e}")

		return InvoiceLineItem(r['create_subitem']['id'], r['create_subitem'])


class InvoiceLineItem(BaseItemType):
	BOARD_ID = 6288579132

	def __init__(self, item_id=None, api_data=None, search=None, cache_data=None):
		self.line_type = columns.StatusValue("status27")
		self.price_inc_vat = columns.NumberValue("numbers")
		self.line_item_id = columns.TextValue("text")
		self.line_description = columns.LongTextValue("line_description")

		self.source_item_id = columns.TextValue("text1")
		self.source_item_connect = columns.ConnectBoards('connect_boards4')

		super().__init__(item_id, api_data, search, cache_data)


class InvoicingError(EricError):
	def __init__(self, message):
		super().__init__(message)


class InvoiceDataError(InvoicingError):
	pass
