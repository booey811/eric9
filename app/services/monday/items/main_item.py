import logging

from ..api import items, columns
from ..api.client import get_api_items
from .product import ProductItem
from .part import PartItem
from ....utilities import notify_admins_of_error

log = logging.getLogger('eric')


class MainItem(items.BaseItemType):
	BOARD_ID = 349212843

	def __init__(self, item_id=None, api_data: dict | None = None):
		# basic info
		self.main_status = columns.StatusValue("status4")
		self.client = columns.StatusValue("status")
		self.service = columns.StatusValue('service')
		self.repair_type = columns.StatusValue('status24')
		self.notifications_status = columns.StatusValue('status_18')

		# contact info
		self.ticket_url = columns.LinkURLValue("link1")
		self.ticket_id = columns.TextValue("text6")
		self.email = columns.TextValue("text5")
		self.phone = columns.TextValue("text00")

		# repair info
		self.products_connect = columns.ConnectBoards("board_relation")
		self.device_connect = columns.ConnectBoards("board_relation5")
		self.description = columns.TextValue("text368")
		self.imeisn = columns.TextValue("text4")

		# payment info
		self.payment_status = columns.StatusValue("payment_status")
		self.payment_method = columns.StatusValue("payment_method")

		# tech info
		self.technician_id = columns.PeopleValue("person")

		# scheduling info
		self.motion_task_id = columns.TextValue("text76")
		self.motion_scheduling_status = columns.StatusValue("status_19")
		self.hard_deadline = columns.DateValue("date36")
		self.phase_deadline = columns.DateValue("date65")

		# thread info
		self.notes_thread_id = columns.TextValue("text37")
		self.email_thread_id = columns.TextValue("text_1")
		self.error_thread_id = columns.TextValue("text34")

		# address info
		self.address_postcode = columns.TextValue("text93")
		self.address_street = columns.TextValue('passcode')
		self.address_notes = columns.TextValue('dup__of_passcode')

		super().__init__(item_id, api_data)

	def load_from_api(self, api_data=None):
		"""
		Load the API data into the model
		"""
		super().load_from_api(api_data)
		self._check_update_threads()

	def _check_update_threads(self):
		if self.id:
			commit = False
			for thread_name in ["EMAIL", "ERROR", "NOTES"]:
				thread_val = getattr(self, f"{thread_name.lower()}_thread_id")
				thread_id = thread_val
				if not thread_id:
					body = f"****** {thread_name} ******"
					update = self.add_update(body)
					thread_val = update['data']['create_update']['id']
					self.staged_changes.update(thread_val.column_api_data())
					commit = True
			if commit:
				self.commit()
		return self

	def get_stock_check_string(self):
		"""
		Checks stock for all products connected to this main item, and return a string description of them
		"""
		log.debug(f"Checking stock for {str(self)}")

		update = '=== STOCK CHECK ===\n'
		try:
			in_stock = True
			product_data = get_api_items(self.products_connect.value)
			prods = [ProductItem(p['id'], p) for p in product_data]
			for prod in prods:
				update += prod.name.upper() + '\n'
				if not prod.parts_connect.value:
					message = f"""No parts connected!!!
					Click to fix my connecting parts to this product by making sure the 'parts' column is filled in
					https://icorrect.monday.com/boards/2477699024/views/55887964/pulses/{prod.id}"""
					notify_admins_of_error(message)
					update += message + '\n'
				else:
					parts_data = get_api_items(prod.parts_connect.value)
					parts = [PartItem(_['id'], _) for _ in parts_data]
					for part in parts:
						update += f"{part.name}: {part.stock_level}\n"

			if in_stock:
				update += "All parts in stock"
			else:
				update += "SOME PARTS MAY NOT BE AVAILABLE"

		except Exception as e:
			log.error(f"Error checking stock for {str(self)}: {e}")
			notify_admins_of_error(f"Error checking stock for {str(self)}: {e}")
			update += f"Error checking stock: {e}"
			raise e

		return update

	@property
	def device_id(self):
		if self.device_connect and self.device_connect.value:
			return self.device_connect.value[0]
		else:
			return None

	@device_id.setter
	def device_id(self, value):
		assert isinstance(value, int)
		self.device_connect = [value]


class PropertyTestItem(items.BaseItemType):
	BOARD_ID = 349212843

	text = columns.TextValue('text69')
	number = columns.NumberValue('dup__of_quote_total')
	status = columns.StatusValue('status_161')
	date = columns.DateValue('date6')
	url_link = columns.LinkURLValue('link1')
	product_connect = columns.ConnectBoards('board_relation')
	long_text = columns.LongTextValue("long_text5")
	people = columns.PeopleValue('person')
	dropdown = columns.DropdownValue("device0")
