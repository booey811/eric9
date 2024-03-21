import abc
import datetime
import calendar
from dateutil.parser import parse

from zenpy.lib.api_objects import Ticket

from ...api.items import BaseItemType
from ...api import columns
from .....services import zendesk, monday, xero
from .....utilities import notify_admins_of_error
from ..sales import InvoiceDataError


class CorporateAccountItem(BaseItemType):
	BOARD_ID = 1973442389

	@classmethod
	def get_by_short_code(cls, short_code):
		search = cls().search_board_for_items('short_code', short_code)
		if len(search) == 1:
			return cls(search[0]['id'], search[0])
		elif len(search) > 1:
			raise ValueError(f"Multiple Corporate Account Items found for short_code {short_code}")
		else:
			raise ValueError(f"No Corporate Account Item found for short_code {short_code}")

	def __init__(self, item_id=None, api_data=None, search=None):

		self.repair_board_id = columns.TextValue("text6")

		self.zen_org_id = columns.TextValue("text9")
		self.xero_contact_id = columns.TextValue("text")

		self.current_invoice_id = columns.TextValue("text1")

		self.invoicing_style = columns.StatusValue("status7")

		self.req_po = columns.CheckBoxValue("checkbox6")
		self.req_cost_code = columns.CheckBoxValue("checkbox_1")
		self.req_username = columns.CheckBoxValue("checkbox_2")

		self.global_po = columns.TextValue("text2")

		self.inv_ref_start = columns.TextValue("text3")
		self.inv_ref_end = columns.TextValue("text12")

		self.courier_price = columns.NumberValue("numbers9")

		super().__init__(item_id, api_data, search)

	def get_current_invoice(self):
		"""Get the current invoice for this account"""

		if self.invoicing_style.value == "Pay Per Repair":
			# we will create and return a new invoice item
			pass
		elif self.invoicing_style.value in ("Monthly Payments", "Batch"):
			# get and return a draft invoice item
			xero_invoices = xero.client.get_invoices_for_contact_id(self.xero_contact_id.value, filter_status="DRAFT")
			if len(xero_invoices) == 1:
				search_results = monday.items.sales.InvoiceControllerItem().search_board_for_items(
					'invoice_id', str(xero_invoices[0]['InvoiceID'])
				)
				if len(search_results) == 1:
					return monday.items.sales.InvoiceControllerItem(search_results[0]['id'], search_results[0])
				elif len(search_results) == 0:
					# create and return an invoice item
					pass
				else:
					notify_admins_of_error(
						f"{str(self)} could Not Find Invoice Item for Invoice {xero_invoices[0]['InvoiceID']}")
					raise ValueError(f"Could Not Find Invoice Item for Invoice {xero_invoices[0]['InvoiceID']}")
			elif len(xero_invoices) > 1:
				raise ValueError(f"Multiple Draft Invoices found for contact_id {self.xero_contact_id.value}")
			elif len(xero_invoices) == 0:
				# we will create and return an invoice item
				pass
			else:
				raise RuntimeError("Mathematically Impossible Error")
		else:
			raise ModuleNotFoundError(f"{str(self)}has invalid invoicing style: {self.invoicing_style.value}")

		# create and return a new invoice item
		invoice_item = monday.items.sales.InvoiceControllerItem()
		invoice_item.corporate_account_connect = [int(self.id)]
		invoice_item.corporate_account_item_id = str(self.id)

		xero_invoice = self.create_blank_xero_invoice()

		invoice_item.invoice_id = xero_invoice['InvoiceID']
		invoice_item.invoice_number = xero_invoice['InvoiceNumber']
		invoice_item.invoice_status = "DRAFT"
		f_date = parse(xero_invoice['DateString']).strftime("%a %d %b")
		invoice_item.create(f"{self.name}: {f_date}")

		return invoice_item

	def apply_account_specific_description(self, sale_item, description):

		if self.req_cost_code.value:
			if not sale_item.cost_centre.value:
				raise InvoiceDataError(f"{str(sale_item)} requires a cost code")
			description += f"\nCost Code: {sale_item.cost_centre.value}"

		if self.req_username:
			if not sale_item.username.value:
				raise InvoiceDataError(f"{str(sale_item)} requires a username")
			description += f"\nUsername: {sale_item.username.value}"

		return description

	def create_blank_xero_invoice(self):
		"""Create a new invoice for this account"""
		basic = {
			"Type": "ACCREC",
			"Contact": {
				"ContactID": self.xero_contact_id.value
			},
			"LineItems": [
				xero.client.make_line_item(
					'Placeholder',
					1,
					0
				)
			]
		}
		now = datetime.datetime.now()

		if self.invoicing_style.value == "Monthly Payments":
			_, last_day = calendar.monthrange(now.year, now.month)
			dt = datetime.date(now.year, now.month, last_day)
		else:
			dt = now

		basic['Date'] = dt.strftime("%Y-%m-%d")

		return xero.client.update_invoice(basic)


class CorporateRepairItem(BaseItemType):
	"""Base class for corporate board items. contains all required methods for enacting the various base processes"""

	def __init__(self, item_id=None, api_data=None, search=None):
		self.ticket_id = None
		self.imeisn = None
		self.device_name = None
		self.description = None
		self.cost = None
		self.main_board_connect = None
		self.courier_cost_inc_vat = None

		self._account_item = None

		column_map = self.get_column_id_map()
		for att in column_map:
			setattr(self, att, column_map[att])

		if self.ticket_id is None or self.imeisn is None or self.device_name is None or self.description is None or self.cost is None:
			raise NotImplementedError("Subclasses must define all attributes.")

		super().__init__(item_id, api_data, search)

	@property
	@abc.abstractmethod
	def account_item(self) -> CorporateAccountItem:
		"""Get the corporate account item associated with this repair item"""
		raise NotImplementedError

	@staticmethod
	@abc.abstractmethod
	def get_column_id_map():
		"""Get the column id map for this item"""
		raise NotImplementedError

	@classmethod
	def get_from_ticket_id(cls, ticket_id) -> 'CorporateRepairItem':
		"""Create a corporate repair from a ticket"""
		search = cls().search_board_for_items('ticket_id', str(ticket_id))

		if len(search) == 1:
			return cls(search[0]['id'], search[0])
		elif len(search) > 1:
			raise ValueError(f"Multiple Corporate Repair Items found for ticket_id {ticket_id}")
		elif len(search) == 0:
			pass
		else:
			raise ValueError(f"No Corporate Repair Item found for ticket_id {ticket_id}")

		# not found, create a new one
		ticket = zendesk.client.tickets(id=int(ticket_id))

		new = cls()
		new.ticket_id = str(ticket_id)
		new.create(name=ticket.requester.name)

		return new

	def sync_changes_from_main(self, main_id):
		"""Sync changes from the main item"""
		main = monday.items.MainItem(main_id)

		# do not sync ticket ID, this should not change after being set

		imeisn = main.imeisn.value
		if imeisn:
			self.imeisn = imeisn

		device = monday.items.DeviceItem(main.device_id)
		device_name = device.name
		if device_name:
			self.device_name = device_name

		products = main.products
		description = ""
		total = 0
		for prod in products:
			stripped = prod.name.replace(device_name, "").strip()
			description += f"{stripped}, "
			total += int(prod.price.value)
		description = description[:-2]
		if description:
			self.description = description

		self.cost = total

		self.commit()
		return self

	def include_courier_costs(self, courier_dump_item):

		# get the courier cost
		cost = courier_dump_item.cost_inc_vat.value

		current_spend = self.courier_cost_inc_vat.value
		if current_spend:
			cost += current_spend

		self.courier_cost_inc_vat = cost
		self.commit()

		return self


class PrototypeCorporateRepairItem(CorporateRepairItem):
	"""Test class for corporate repair items"""

	BOARD_ID = 6105662756

	def __init__(self, item_id=None, api_data=None, search=None):
		super().__init__(item_id, api_data, search)

	@property
	def account_item(self) -> CorporateAccountItem:
		if not self._account_item:
			self._account_item = CorporateAccountItem(1985121455)
		return self._account_item

	@staticmethod
	def get_column_id_map():
		return {
			"ticket_id": columns.TextValue("text4"),
			"imeisn": columns.TextValue("text"),
			"device_name": columns.TextValue("text9"),
			"description": columns.LongTextValue("long_text"),
			"cost": columns.NumberValue("numbers"),
			"main_board_connect": columns.ConnectBoards("connect_boards")
		}
