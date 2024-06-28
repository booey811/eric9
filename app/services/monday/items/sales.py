import logging
import datetime
import math
import json
from dateutil.parser import parse

from ....errors import EricError
from ....utilities import notify_admins_of_error, users
from ... import zendesk, monday, xero
from ..api.items import BaseItemType
from ..api import columns
from . import MainItem

log = logging.getLogger('eric')


class SaleControllerItem(BaseItemType):
	BOARD_ID = 6285416596

	def __init__(self, item_id=None, api_data=None, search=None, cache_data=None):
		self.main_item_id = columns.TextValue("text")
		self.main_item_connect = columns.ConnectBoards("connect_boards")

		self.processing_status = columns.StatusValue("status4")
		self.convert_to_pl_status = columns.StatusValue("status5")

		self.invoicing_status = columns.StatusValue("status1")
		self.invoice_line_item_id = columns.TextValue("text018")
		self.invoice_line_item_connect = columns.ConnectBoards("board_relation")

		self.corporate_account_connect = columns.ConnectBoards("connect_boards0")
		self.corporate_account_item_id = columns.TextValue("text00")
		self.price_override = columns.NumberValue("numbers7")

		self.cost_centre = columns.TextValue("text3")
		self.username = columns.TextValue("text9")

		self.date_added = columns.DateValue("date4")

		self.subitem_ids = columns.ConnectBoards("subitems")
		self.device_type = columns.TextValue("text__1")
		self.parts_cost = columns.NumberValue("numbers7__1")

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
					raise InvoiceDataError(
						f"No corporate account reference found for {organization.name}, please select a Corporate "
						f"Account in the 'Corporate Account' column"
					)
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
			elif self.invoice_line_item_connect.value:
				self.add_update(
					"Already pushed to invoicing, please delete the connected line item to re-add to invoice")
				self.invoicing_status = "Pushed to Invoicing"
				self.commit()
				return self
			elif self.processing_status.value != "Complete":
				self.invoicing_status = "No Products"
				self.commit()
				self.add_update(
					"Cannot add to invoice as there is no product data for the item. Go Back to the default view and "
					"ensure the Product Assignment Process has been completed for this Sale"
				)
				return self
			else:
				corp_item = self.get_corporate_account_item()
				invoice_item = corp_item.get_current_invoice(self.name)
				if not main_item.device_id:
					raise InvoiceDataError("No Device Attached to Main Item. This is required for invoicing")
				device = monday.items.device.DeviceItem(main_item.device_id)
				repairs = [monday.items.sales.SaleLineItem(item_id=item_id) for item_id in self.subitem_ids.value]
				repair_total = 0
				repair_description = device.name
				for repair in repairs:
					repair_total += int(repair.price_inc_vat.value)
					repair_description += f'{repair.name.replace(device.name, "")}, '

				# custom_ids = main_item.custom_quote_connect.value
				# if custom_ids:
				# 	custom_data = monday.api.get_api_items(custom_ids)
				# 	custom_items = [monday.items.misc.CustomQuoteLineItem(d['id'], d) for d in custom_data]
				# 	for custom in custom_items:
				# 		repair_total += int(custom.price.value)
				# 		repair_description += f'{custom.name}, '

				if self.date_added.value:
					date_desc = "\nRepair Date: " + self.date_added.value.strftime("%d/%m/%Y")
				else:
					date_desc = '\nRepair Date: N/A'

				repair_description = repair_description[:-2]
				repair_description += "\nIMEI/SN: " + main_item.imeisn.value
				repair_description += date_desc
				repair_description += "\nRequested By: " + main_item.name

				repair_description = corp_item.apply_account_specific_description(self, repair_description)

				name = self.name
				if self.price_override.value:
					repair_total = self.price_override.value
					name = f"{self.name} (Price Has Been Overridden)"
				line_item = invoice_item.add_invoice_line(
					item_name=name,
					description=repair_description,
					total_price=repair_total,
					line_type="Repairs",
					source_item=self,
					main_item_id=self.main_item_id.value,
					zendesk_id=main_item.ticket_id.value
				)
				self.invoice_line_item_connect = [int(line_item.id)]
				self.invoice_line_item_id = str(line_item.id)

				if corp_item.courier_price.value == 0:
					# corporate account does not pay for couriers
					pass
				else:
					if corp_item.courier_price.value:
						# corporate account has a fixed courier price
						courier_costs = round(float(corp_item.courier_price.value) * 2, 2)
						source = corp_item
					else:
						courier_item_search = monday.items.misc.CourierDataDumpItem(search=True).search_board_for_items(
							"main_item_id",
							str(self.main_item_id.value)
						)
						if courier_item_search:
							try:
								courier_item = [
									monday.items.misc.CourierDataDumpItem(item['id'], item) for item in
									courier_item_search
								][0]
								courier_costs = math.ceil(courier_item.cost_inc_vat.value * 2)
								source = courier_item
							except ValueError:
								courier_costs = 20
								source = None
						else:
							courier_costs = 20
							source = None

					description = f"Courier Service ({self.get_main_item().address_postcode.value})"
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

		# self.corporate_account_item_id = columns.TextValue("text9")
		self.corporate_account_connect = columns.ConnectBoards("connect_boards0")
		self.po_number = columns.TextValue("text__1")

		self.invoice_id = columns.TextValue("text8")
		self.invoice_number = columns.TextValue("text0")

		self.xero_sync_status = columns.StatusValue("status4")

		self.invoice_status = columns.StatusValue("status58")

		self.subitem_ids = columns.ConnectBoards("subitems")

		super().__init__(item_id, api_data, search, cache_data)

	def add_invoice_line(self, item_name, description, total_price, line_type, source_item, main_item_id=None, zendesk_id=None) -> "InvoiceLineItem":
		if not self.id:
			raise ValueError(f"{str(self)} Cannot create subitem as it has no parent item ID")
		blank = InvoiceLineItem()
		blank.line_description = description
		blank.price_inc_vat = total_price
		blank.line_type = line_type
		blank.source_item_id = str(source_item.id)
		blank.source_item_url = [str(source_item.name),
								 f"https://icorrect.monday.com/boards/{source_item.BOARD_ID}/pulses/{source_item.id}"]
		if main_item_id:
			blank.connect_main_item = [int(main_item_id)]
		if zendesk_id:
			blank.zendesk_url = [
				zendesk_id, f"https://icorrect.zendesk.com/agent/tickets/{zendesk_id}"
			]
		r = monday.api.monday_connection.items.create_subitem(
			parent_item_id=int(self.id),
			subitem_name=item_name,
			column_values=blank.staged_changes
		)

		if r.get('error_message'):
			notify_admins_of_error(f"Error creating invoice line item: {r['error_message']}")
			raise InvoiceDataError(f"Error creating invoice line item on Monday: {r['error_message']}")

		return InvoiceLineItem(r['data']['create_subitem']['id'], r['data']['create_subitem'])

	def sync_to_xero(self):
		try:
			if not self.po_number.value:
				corporate_account_item = monday.items.corporate.base.CorporateAccountItem(
					self.corporate_account_item_id.value)
				if corporate_account_item.req_po.value:
					raise InvoiceDataError(
						"A PO Number is required for this Corporate Account. Please add this to the 'PO Number/Invoice"
						" Reference' column and try again"
					)

			if not self.invoice_id.value:
				# we will need to create the invoice in xero
				corp_item = monday.items.corporate.base.CorporateAccountItem(self.corporate_account_item_id.value)
				xero_data = {
					"Type": "ACCREC",
					"Contact": {
						"ContactID": str(corp_item.xero_contact_id.value)
					},
					"LineItems": [],
					"Status": "DRAFT",
				}
			else:
				xero_data = xero.client.get_invoice_by_id(self.invoice_id.value)

			if not xero_data:
				raise InvoiceDataError(f"Cannot Sync to Xero: Invoice {self.invoice_id.value} Not Found")
			elif xero_data['Status'] != "DRAFT":
				raise InvoiceDataError(f"Cannot Sync to Xero: Invoice {self.invoice_id.value} is not in DRAFT status")

			inv_lines_from_monday = [
				monday.items.sales.InvoiceLineItem(item_id=item_id) for item_id in self.subitem_ids.value
			]

			xero_data['LineItems'] = []

			for line in inv_lines_from_monday:
				self.add_update("Adding Line Item to Invoice: " + line.line_description.value)
				xero_data['LineItems'].append(
					xero.client.make_line_item(
						description=line.line_description.value,
						quantity=1,
						unit_amount=round(line.price_inc_vat.value / 1.2, 2),
					)
				)

			if self.po_number.value:
				xero_data['Reference'] = self.po_number.value

			xero_invoice = xero.client.update_invoice(xero_data)
			for line_item in xero_invoice['LineItems']:
				for line in inv_lines_from_monday:
					if line.line_description.value == line_item['Description']:
						line.line_item_id = line_item['LineItemID']
						line.commit()

			self.invoice_id = xero_invoice['InvoiceID']
			self.invoice_number = xero_invoice['InvoiceNumber']

			self.invoice_status = "DRAFT"
			self.xero_sync_status = "Synced"
			self.commit()
		except Exception as e:
			self.xero_sync_status = "Error"
			self.commit()
			self.add_update(f"Error syncing to xero: {e}")
			raise e


class InvoiceLineItem(BaseItemType):
	BOARD_ID = 6288579132

	def __init__(self, item_id=None, api_data=None, search=None, cache_data=None):
		self.line_type = columns.StatusValue("status27")
		self.price_inc_vat = columns.NumberValue("numbers")
		self.line_item_id = columns.TextValue("text")
		self.line_description = columns.LongTextValue("line_description")

		self.source_item_id = columns.TextValue("text1")
		self.source_item_url = columns.LinkURLValue('link')

		self.connect_main_item = columns.ConnectBoards("connect_boards__1")
		self.zendesk_url = columns.LinkURLValue("link__1")

		super().__init__(item_id, api_data, search, cache_data)


class WasItWorthItItem(BaseItemType):
	BOARD_ID = 6310609889

	def __init__(self, item_id=None, api_data=None, search=None, cache_data=None):
		self.imeisn = columns.TextValue("text84")
		self.device_connect = columns.ConnectBoards("connect_boards")
		self.device_id = columns.TextValue("text3")

		self.sale_items_connect = columns.ConnectBoards("connect_boards2")

		self.calculation_status = columns.StatusValue("status")

		self.date_added = columns.DateValue("date")
		self.subitem_ids = columns.ConnectBoards("subitems")

		super().__init__(item_id, api_data, search, cache_data)

	def _add_sub_line(self, name, line_type, costs, revenue, source_item, notes=''):
		blank = WasItWorthItLineItem()
		blank.source_item_id = str(source_item.id)
		blank.source_item_url = [str(source_item.name),
								 f"https://icorrect.monday.com/boards/{source_item.BOARD_ID}/pulses/{source_item.id}"]
		blank.line_type = line_type
		if costs:
			blank.cost = costs
		if revenue:
			blank.revenue = revenue
		if notes:
			blank.notes = notes
		r = monday.api.monday_connection.items.create_subitem(
			parent_item_id=int(self.id),
			subitem_name=name,
			column_values=blank.staged_changes
		)

		if r.get('error_message'):
			notify_admins_of_error(f"Error creating sub line item: {r['error_message']}")
			raise WasItWorthItError(f"Error creating sub line item on Monday: {r['error_message']}")

		return r['data']['create_subitem']['id'], r['data']['create_subitem']

	def add_parts_cost(self, main_item, sale_item):
		stock_checkout_item = None
		if not main_item.stock_checkout_id.value:
			sc_search = monday.items.part.StockCheckoutControlItem(search=True).search_board_for_items(
				"main_item_id",
				str(main_item.id)
			)
			if sc_search:
				main_item.stock_checkout_id = sc_search[0]['id']
				main_item.commit()
				stock_checkout_item = monday.items.part.StockCheckoutControlItem(sc_search[0]['id'], sc_search[0])
			else:
				self.add_update("No Stock Checkout Item Found, No Parts Cost Applied")
		else:
			stock_checkout_item = monday.items.part.StockCheckoutControlItem(
				main_item.stock_checkout_id.value).load_from_api()
		if stock_checkout_item:
			stock_line_data = monday.api.get_api_items(stock_checkout_item.checkout_line_ids.value)
			stock_checkout_lines = [
				monday.items.part.StockCheckoutLineItem(item['id'], item) for item in stock_line_data
			]
			parts_cost = sum([float(line.parts_cost.value) for line in stock_checkout_lines])
			self._add_sub_line(
				name=f"Parts Cost: {sale_item.name} ({sale_item.date_added.value.strftime('%d/%m/%Y')})",
				line_type="Parts Cost",
				costs=parts_cost,
				revenue=None,
				source_item=stock_checkout_item
			)

	def add_courier_costs(self, main_item, sale_item):
		courier_search = monday.items.misc.CourierDataDumpItem(search=True).search_board_for_items(
			"main_item_id",
			str(main_item.id)
		)
		if courier_search:
			courier_data = [monday.items.misc.CourierDataDumpItem(item['id'], item) for item in courier_search]
			courier_costs = sum([float(c.cost_inc_vat.value) for c in courier_data])
			self._add_sub_line(
				name=f"Courier Costs: {sale_item.name} ({sale_item.date_added.value.strftime('%d/%m/%Y')})",
				line_type="Logistics Costs",
				costs=courier_costs,
				revenue=None,
				source_item=courier_data[0]
			)

	def add_labour_costs(self, main_item):
		session_search = monday.items.misc.RepairSessionItem(search=True).search_board_for_items(
			"main_board_id",
			str(main_item.id)
		)
		if session_search:
			session_data = [monday.items.misc.RepairSessionItem(item['id'], item) for item in session_search]
			sessions_by_technician = {}
			for session in session_data:
				technician = users.User(monday_id=session.technician.value[0])
				if technician.monday_id not in sessions_by_technician:
					sessions_by_technician[technician.monday_id] = []
				sessions_by_technician[technician.monday_id].append(session)
			for tech_id in sessions_by_technician:
				technicians_sessions = sessions_by_technician[tech_id]
				sessions_duration_in_mins = sum(
					[float(s.get_session_duration()) for s in technicians_sessions]
				)
				technician = users.User(monday_id=tech_id)
				hourly_rate = technician.get_staff_item().internal_hourly_rate.value

				session_costs = sessions_duration_in_mins / 60 * hourly_rate

				note = f"{sessions_duration_in_mins} minutes @ {hourly_rate} per hour"
				self._add_sub_line(
					name=f"Session Costs: {technician.name.title()}",
					line_type="Labour Cost",
					costs=session_costs,
					revenue=None,
					source_item=session_data[0],
					notes=note
				)

	def add_sale_revenue(self, sale_item):
		sale_revenue_data = monday.api.get_api_items(sale_item.subitem_ids.value)
		sale_lines = [SaleLineItem(item['id'], item) for item in sale_revenue_data]
		sale_revenue = sum([float(line.price_inc_vat.value) for line in sale_lines])
		self._add_sub_line(
			name=f"Sale Revenue: {sale_item.name} ({sale_item.date_added.value.strftime('%d/%m/%Y')})",
			line_type="Sale",
			costs=None,
			revenue=sale_revenue,
			source_item=sale_item
		)

	def calculate_profit_loss(self):

		# remove old lines
		current_sub_line_ids = self.subitem_ids.value
		if current_sub_line_ids:
			for _ in current_sub_line_ids:
				monday.api.monday_connection.items.delete_item_by_id(_)

		try:
			if not self.sale_items_connect.value:
				raise WasItWorthItError("No Sale Items Connected")

			sale_item_data = monday.api.get_api_items(self.sale_items_connect.value)
			sale_items = [SaleControllerItem(item['id'], item) for item in sale_item_data]

			for sale in sale_items:
				main_item = MainItem(sale.main_item_id.value).load_from_api()
				if not main_item:
					raise WasItWorthItError("Main Item Not Found")

				self.add_parts_cost(main_item, sale)
				self.add_sale_revenue(sale)
				self.add_courier_costs(main_item, sale)
				self.add_labour_costs(main_item)

			self.calculation_status = "Complete"
			self.commit()
			return self

		except Exception as e:
			self.calculation_status = "Error"
			self.commit()
			self.add_update(f"Error calculating profit/loss: {e}")
			raise e


class WasItWorthItLineItem(BaseItemType):
	BOARD_ID = 6310611850

	def __init__(self, item_id=None, api_data=None, search=None, cache_data=None):
		self.line_type = columns.StatusValue("status")
		self.cost = columns.NumberValue("numbers")
		self.revenue = columns.NumberValue("numbers1")

		self.source_item_id = columns.TextValue("text")
		self.source_item_url = columns.LinkURLValue('link')

		self.is_warranty = columns.CheckBoxValue("checkbox")

		self.notes = columns.LongTextValue("long_text")

		super().__init__(item_id, api_data, search, cache_data)


class ProductSalesLedgerItem(BaseItemType):
	BOARD_ID = 6894117865

	def __init__(self, item_id=None, api_data=None, search=None):

		self.date_sold = columns.DateValue("date4")
		self.device_id = columns.TextValue("text9__1")
		self.device_name = columns.TextValue("text__1")
		self.device_type = columns.TextValue("text7__1")
		self.product_id = columns.TextValue("text5__1")
		self.product_type = columns.TextValue("text2__1")
		self.sale_subitem_id = columns.TextValue("text55__1")
		self.price_at_pos = columns.NumberValue("numbers__1")
		self.sale_item_id = columns.TextValue("text74__1")
		self.sale_subitem_type = columns.StatusValue("status__1")

		super().__init__(item_id, api_data, search)

	@classmethod
	def create_new_record(cls, sale_item_id, delete_old_record=True):
		comments = []
		try:
			sale_item = SaleControllerItem(sale_item_id)
			log.info(f"Creating Product Ledger Record for Sale Item: {sale_item.name} ({sale_item.date_added.value})")
			sale_item.load_from_api()
			try:
				main_item = sale_item.get_main_item()
			except Exception as e:
				new = cls()
				new.sale_item_id = str(sale_item_id)
				new.create(f"{sale_item.name} - Error Fetching Main Item")
				monday.api.monday_connection.updates.create_update(
					item_id=new.id,
					update_value=f"Error creating Product Ledger Record\n\nError Fetching Main Item: {str(e)}",
				)
				return False
			if main_item.device_id:
				try:
					device = monday.items.DeviceItem.get([main_item.device_id])[0]
				except IndexError:
					# use default device
					comments.append('Could Not Find Device, Using Default Device (Other Device)')
					device = monday.items.DeviceItem(4028854241)  # other device ID
			else:
				# use default device
				comments.append('Device Not Assigned to Main Item, Using Default Device (Other Device)')
				device = monday.items.DeviceItem(4028854241)  # other device ID
			device_id = device.id
			device_name = device.name
			device_type = device.device_type.value
			subitem_query = monday.api.monday_connection.items.fetch_subitems(sale_item_id)
			if subitem_query.get('error_message'):
				new = cls()
				new.sale_item_id = str(sale_item_id)
				new.create(f"{sale_item.name} - Error Fetching Subitems")
				raise Exception(f"Error fetching Sale Subitems: {subitem_query['error_message']}")
			else:
				subitem_data = subitem_query['data']['items'][0]['subitems']
			for sale_subitem_id in [int(_['id']) for _ in subitem_data]:
				try:
					# check record doesn't already exist
					existing_query = monday.api.monday_connection.items.fetch_items_by_column_value(
						board_id=cls.BOARD_ID,
						column_id="text55__1",  # sale_subitem_id
						value=str(sale_subitem_id)
					)
					if existing_query.get('error_message'):
						raise Exception(
							f"Error checking if Product Ledger Record Exists: {existing_query['error_message']}")
					elif existing_query['data']['items_page_by_column_values']['items']:
						if not delete_old_record:
							continue
						# delete the item, we will make a new one
						monday.api.monday_connection.items.delete_item_by_id(
							existing_query['data']['items_page_by_column_values']['items'][0]['id']
						)
					elif not existing_query['data']['items_page_by_column_values']['items']:
						pass

					# get the sale subitem
					sale_subitem = SaleLineItem(sale_subitem_id)
					new = cls()
					if sale_subitem.line_type.value == "Custom Quote":
						subitem_type = "Custom Quote"
						product_type = "Custom Product"
						product_id = "Custom Product"
					elif sale_subitem.line_type.value == "Standard Product":
						subitem_type = "Standard Product"
						product = monday.items.product.ProductItem(sale_subitem.source_id.value)
						product_id = product.id
						product_type = product.product_type.value
					else:
						subitem_type = "Other"
						product_type = 'Unknown'
						product_id = "Unknown"
						comments.append(f"Unknown Sale Subitem Type: {sale_subitem.line_type.value}, setting to Other")
						comments.append("Could not find any product info, using 'Unknown' for product type")

					date = sale_item.date_added.value
					if not date:
						comments.append("Sale Item missing date info, getting from Main Item")
						date = main_item.repaired_date.value
						if not date:
							for col_data in sale_subitem._column_data:
								if col_data['id'] == 'creation_log__1':
									created_at_dict = json.loads(col_data['value'])
									created_at_dt = parse(created_at_dict['created_at'])
									date = created_at_dt
									break
							else:
								comments.append("Could not find any date info, using today's date")
								date = datetime.datetime.now()

					new.sale_item_id = str(sale_item_id)
					new.date_sold = date
					new.device_id = str(device_id)
					new.device_name = str(device_name)
					new.device_type = str(device_type)
					new.price_at_pos = sale_subitem.price_inc_vat.value
					new.sale_subitem_id = str(sale_subitem_id)
					new.sale_subitem_type = subitem_type
					new.product_id = str(product_id)
					new.product_type = str(product_type)

					new.create(sale_subitem.name)

					if comments:
						new.add_update("\n".join(comments))

				except Exception as e:
					error_messages = "\n".join(comments)
					error_messages += f"\n{str(e)}"
					monday.api.monday_connection.updates.create_update(
						item_id=sale_subitem_id,
						update_value=f"Error creating Product Ledger Record\n\n{error_messages}",
					)

		except Exception as e:
			notify_admins_of_error(f"Error creating Product Ledger Record: {e}")
			monday.api.monday_connection.updates.create_update(
				item_id=sale_item_id,
				update_value=f"Error creating Product Ledger Record: {e}",
			)


class InvoicingError(EricError):
	def __init__(self, message):
		super().__init__(message)


class InvoiceDataError(InvoicingError):
	pass


class WasItWorthItError(EricError):
	pass
