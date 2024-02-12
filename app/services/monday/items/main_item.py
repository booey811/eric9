import logging

from ..api import items, columns, get_api_items
from .product import ProductItem
from .part import PartItem
from ....utilities import notify_admins_of_error

log = logging.getLogger('eric')


class MainItem(items.BaseItemType):
	BOARD_ID = 349212843

	# basic info
	main_status = columns.StatusValue("status4")

	# repair info
	products_connect = columns.ConnectBoards("board_relation")
	description = columns.TextValue("text368")

	# tech info
	technician_id = columns.PeopleValue("person")

	# scheduling info
	motion_task_id = columns.TextValue("text76")
	motion_scheduling_status = columns.StatusValue("status_19")
	hard_deadline = columns.DateValue("date36")
	phase_deadline = columns.DateValue("date65")

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
