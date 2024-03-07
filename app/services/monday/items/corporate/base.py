import abc
from typing import Type

from zenpy.lib.api_objects import Ticket

from ...api.items import BaseItemType
from ...api import columns
from .....services import zendesk, monday


class CorporateAccountItem(BaseItemType):
	BOARD_ID = 1973442389


class CorporateRepairItem(BaseItemType):
	"""Base class for corporate board items. contains all required methods for enacting the various base processes"""

	def __init__(self, item_id=None, api_data=None, search=None):
		self.ticket_id = None
		self.imeisn = None
		self.device_name = None
		self.description = None
		self.cost = None
		self.main_board_connect = None

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
