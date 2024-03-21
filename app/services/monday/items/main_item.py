import logging
import json

from ..api import items, columns, boards
from ..api.client import get_api_items
from .product import ProductItem
from .part import PartItem, RepairMapItem
from . import repair_phases
from ....utilities import notify_admins_of_error

log = logging.getLogger('eric')


class MainItem(items.BaseItemType):
	BOARD_ID = 349212843

	def __init__(self, item_id=None, api_data: dict | None = None, search=False):
		# basic info
		self.main_status = columns.StatusValue("status4")
		self.client = columns.StatusValue("status")
		self.service = columns.StatusValue('service')
		self.repair_type = columns.StatusValue('status24')
		self.notifications_status = columns.StatusValue('status_18')
		self.booking_date = columns.DateValue("date6")
		self.date_received = columns.DateValue("date4")

		# contact info
		self.ticket_url = columns.LinkURLValue("link1")
		self.ticket_id = columns.TextValue("text6")
		self.email = columns.TextValue("text5")
		self.phone = columns.TextValue("text00")

		# repair info
		self.products_connect = columns.ConnectBoards("board_relation")
		self.device_connect = columns.ConnectBoards("board_relation5")
		self.custom_quote_connect = columns.ConnectBoards("board_relation0")
		self.description = columns.TextValue("text368")
		self.imeisn = columns.TextValue("text4")
		self.passcode = columns.TextValue('text8')
		self.repaired_date = columns.DateValue("collection_date")

		self.stock_checkout_id = columns.TextValue("text766")

		self.device_deprecated_dropdown = columns.DropdownValue("device0")
		self.parts_used_dropdown = columns.DropdownValue("repair")
		self.device_colour = columns.StatusValue("status8")

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

		self.repair_phase = columns.StatusValue("status_177")
		self.phase_status = columns.StatusValue("status_110")

		# thread info
		self.notes_thread_id = columns.TextValue("text37")
		self.email_thread_id = columns.TextValue("text_1")
		self.error_thread_id = columns.TextValue("text34")

		# address info
		self.address_postcode = columns.TextValue("text93")
		self.address_street = columns.TextValue('passcode')
		self.address_notes = columns.TextValue('dup__of_passcode')
		self.company_name = columns.TextValue("text15")

		self.be_courier_collection = columns.StatusValue("be_courier_collection")
		self.be_courier_return = columns.StatusValue("be_courier_return")

		# customer info
		self.corp_item_id = columns.TextValue("text7")

		# properties
		self._products = None

		super().__init__(item_id, api_data, search)
		self._check_update_threads()

	def create(self, name, reload=True):
		super().create(name)
		if reload:
			self.load_from_api()
			self._check_update_threads()
		return self

	def _check_update_threads(self):
		if self.id:
			commit = False
			for thread_name in ["EMAIL", "ERROR", "NOTES"]:
				thread_val = getattr(self, f"{thread_name.lower()}_thread_id")
				thread_id = thread_val.value
				if not thread_id:
					body = f"****** {thread_name} ******"
					update = self.add_update(body)
					thread_val.value = update['data']['create_update']['id']
					self.staged_changes.update(thread_val.column_api_data())
					commit = True
			if commit:
				self.commit()
		return self

	def get_stock_check_string(self, product_ids: list[int | str] | None = None):
		"""
		Checks stock for all products connected to this main item, and return a string description of them
		"""
		log.debug(f"Checking stock for {str(self)}")

		update = '=== STOCK CHECK ===\n'
		try:
			in_stock = True
			if product_ids:
				product_data = get_api_items(product_ids)
			else:
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

	@property
	def products(self):
		if not self._products:
			if self.products_connect.value:
				product_data = get_api_items(self.products_connect.value)
				self._products = [ProductItem(p['id'], p) for p in product_data]
			else:
				self._products = []
		return self._products

	def get_phase_model(self) -> repair_phases.RepairPhaseModel:
		"""collects all products related to this main item and returns the longest available phase model"""
		if not self.products_connect.value:
			# no products connected, use default phase model
			return repair_phases.RepairPhaseModel(6106627585)
		else:
			product_data = get_api_items(self.products_connect.value)
			prods = [ProductItem(p['id'], p) for p in product_data]
			phase_models = [p.get_phase_model() for p in prods]
			return max(phase_models, key=lambda x: x.get_total_minutes_required())

	def generate_repair_map_value_list(self):
		"""creates a list of lists of combined IDS and Dual IDs for use in Repair Map searching"""
		try:
			main_board = boards.get_board(self.BOARD_ID)
			device_no = self.device_deprecated_dropdown.value[0]
			colour_label = self.device_colour.value
			colour_col_settings = json.loads([c for c in main_board['columns'] if c['id'] == str(self.device_colour.column_id)][0]['settings_str'])
			colour_no = None
			for _id, _label in colour_col_settings['labels'].items():
				if str(_label) == str(colour_label):
					colour_no = _id
					break

			results = []

			for pu_id in self.parts_used_dropdown.value:
				pu_text = self.convert_dropdown_ids_to_labels([pu_id], self.parts_used_dropdown.column_id)[0]
				if pu_text in RepairMapItem.REPAIRS_WITH_COLOUR:
					combined_id = f"{device_no}-{pu_id}-{colour_no}"
				else:
					combined_id = f"{device_no}-{pu_id}"
				dual_id = f"{device_no}-{pu_id}"

				results.append([combined_id, dual_id])
			return results
		except Exception as e:
			notify_admins_of_error(f"Could Not Generate Repair Map ID List from {self}")
			raise e

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
