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
				corporate_account_item_id = organization.organization_fields['monday_corporate_id']
				if not corporate_account_item_id:
					raise InvoiceDataError(f"No corporate account reference found for {organization['name']}, please assign a Corporate Account Link")
				i = monday.items.corporate.base.CorporateAccountItem(corporate_account_item_id)
			self._corporate_account_item = i
			self.corporate_account_item_id = str(self._corporate_account_item.id)
			self.corporate_account_connect = [int(self._corporate_account_item.id)]
			self.commit()

		return self._corporate_account_item

	def add_to_invoice_item(self):
		main_item = MainItem(self.main_item_id.value)
		invoice_item = None
		try:
			if main_item.client.value == "End User":
				self.invoicing_status = "Not Corporate"
				self.commit()
				return self
			elif main_item.client.value == "Warranty":
				self.invoicing_status = "Warranty"
				self.commit()
				return self
			elif self.invoice_line_item_id.value:
				notify_admins_of_error(f"Blocked attempt to regenerate invoice: {str(self)}")
				self.add_update("Already pushed to invoicing, please delete any connected items and try again.")
				self.invoicing_status = "Pushed to Invoicing"
				self.commit()
				return self
			elif self.processing_status.value != "Complete":
				self.invoicing_status = "Missing Info"
				self.commit()
				return self
			else:
				corp_item = self.get_corporate_account_item()
				invoice_item = corp_item.get_current_invoice()
				if not invoice_item.id:
					invoice_item.create(corp_item.name)
				device = monday.items.device.DeviceItem(main_item.device_id)
				repairs = [monday.items.sales.SaleLineItem(item_id=item_id) for item_id in self.subitem_ids.value]
				repair_total = 0
				repair_description = device.name
				for repair in repairs:
					repair_total += int(repair.price_inc_vat.value)
					repair_description += f'{repair.name.replace(device.name, "")}, '
				repair_description = repair_description[:-2]

				name = self.name
				if self.price_override.value:
					repair_total = self.price_override.value
					name = f"{self.name} (Price Has Been Overridden)"
				line_item = invoice_item.add_invoice_line(
					item_name=name,
					description=repair_description,
					total_price=repair_total,
					line_type="Repairs",
					source_item=self
				)
				self.invoice_line_item_connect = [int(line_item.id)]
				self.invoice_line_item_id = str(line_item.id)

				courier_item_search = monday.items.misc.CourierDataDumpItem(search=True).search_board_for_items(
					"main_item_id",
					str(self.main_item_id.value)
				)
				if courier_item_search:
					if corp_item.courier_price.value:
						one_way = corp_item.courier_price.value
						courier_costs = float(one_way) * len(courier_item_search)
						description = f"{len(courier_item_search)} Jobs @ {one_way} each"
						source = corp_item
					else:
						courier_items = [
							monday.items.misc.CourierDataDumpItem(item['id'], item) for item in courier_item_search
						]
						courier_costs = 0
						for courier in courier_items:
							courier_costs += float(courier.cost_inc_vat.value)
						description = f"{len(courier_item_search)} Jobs ({self.get_main_item().address_postcode.value})"
						source = courier_items[0]
					invoice_line_item = invoice_item.add_invoice_line(
						item_name="Courier Costs",
						description=description,
						total_price=courier_costs,
						line_type="Logistics",
						source_item=source
					)

				self.invoicing_status = "Pushed to Invoicing"
				self.commit()

		except Exception as e:
			notify_admins_of_error(f"Error adding sale to invoice: {e}")
			if invoice_item:
				monday.api.monday_connection.items.delete_item_by_id(int(invoice_item.id))
			self.invoicing_status = "Error"
			self.commit()
			self.add_update(f"Error adding sale to invoice: {e}")
			raise e


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

	def add_invoice_line(self, item_name, description, total_price, line_type, source_item) -> "InvoiceLineItem":
		if not self.id:
			raise ValueError(f"{str(self)} Cannot create subitem as it has no parent item ID")
		blank = InvoiceLineItem()
		blank.line_description = description
		blank.price_inc_vat = total_price
		blank.line_type = line_type
		blank.source_item_id = str(source_item.id)
		blank.source_item_url = [str(source_item.name), f"https://icorrect.monday.com/boards/{source_item.BOARD_ID}/pulses/{source_item.id}"]
		r = monday.api.monday_connection.items.create_subitem(
			parent_item_id=int(self.id),
			subitem_name=item_name,
			column_values=blank.staged_changes
		)

		if r.get('error_message'):
			notify_admins_of_error(f"Error creating invoice line item: {r['error_message']}")
			raise InvoiceDataError(f"Error creating invoice line item on Monday: {r['error_message']}")

		return InvoiceLineItem(r['data']['create_subitem']['id'], r['data']['create_subitem'])


class InvoiceLineItem(BaseItemType):
	BOARD_ID = 6288579132

	def __init__(self, item_id=None, api_data=None, search=None, cache_data=None):
		self.line_type = columns.StatusValue("status27")
		self.price_inc_vat = columns.NumberValue("numbers")
		self.line_item_id = columns.TextValue("text")
		self.line_description = columns.LongTextValue("line_description")

		self.source_item_id = columns.TextValue("text1")
		self.source_item_url = columns.LinkURLValue('link')

		super().__init__(item_id, api_data, search, cache_data)


class InvoicingError(EricError):
	def __init__(self, message):
		super().__init__(message)


class InvoiceDataError(InvoicingError):
	pass