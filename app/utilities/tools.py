import inspect
import importlib
import pkgutil

import html2text

from ..services.monday import items as items_package, api as api_package
from ..services.monday.api.columns import ValueType
from ..services import monday


class MondayTools:

	@staticmethod
	def find_class_with_board_id(b_id):
		package = items_package
		prefix = package.__name__ + "."

		for importer, modname, ispkg in pkgutil.iter_modules(package.__path__, prefix):
			module = importlib.import_module(modname)
			for name, obj in inspect.getmembers(module, inspect.isclass):
				if hasattr(obj, 'BOARD_ID'):
					if str(obj.BOARD_ID) == str(b_id):
						return obj
		return None

	@staticmethod
	def list_redundant_columns(board_id, delete_columns=False):
		"""
		Find columns that are not used by any items in the board
		"""
		desired_class = MondayTools.find_class_with_board_id(board_id)
		if not desired_class:
			raise Exception(f"Class not found for board_id:{board_id}")

		class_col_ids = []
		desired_instance = desired_class()
		instance_attributes = vars(desired_instance)
		for i_att in instance_attributes:
			if hasattr(instance_attributes[i_att], 'column_id'):
				class_col_ids.append(instance_attributes[i_att].column_id)

		board = api_package.boards.get_board(board_id)
		board_columns = board['columns']

		unused_ids = []
		for b_col in board_columns:
			if b_col['id'] not in class_col_ids:
				if b_col['type'] not in ('name', 'subtasks'):
					print(f"Column {b_col['title']} ({b_col['id']}) is not used by any items in the board")
					unused_ids.append(b_col['id'])

		return unused_ids

	@staticmethod
	def convert_updates_to_text_file(updates, file_path):
		"""
		Convert a list of updates to a text file
		"""

		# Create a new HTML2Text object
		h = html2text.HTML2Text()
		# Ignore converting links from HTML
		h.ignore_links = True

		with open(file_path, 'w') as f:
			for update in updates:
				text = h.handle(update['body'])
				final = f"Note from User({update['creator']['id']})\nTimestamp:{update['created_at']}\n\n{text}\n====================\n\n"
				f.write(final)
		return file_path


class ETLFunctions:

	@staticmethod
	def etl_device_type_in_sales():
		api_data = monday.api.get_items_by_board_id(6285416596)
		sales = [monday.items.sales.SaleControllerItem(_['id'], _) for _ in api_data]
		for sale in sales:
			try:
				main = sale.get_main_item()
				if main.device_id:
					device = monday.items.device.DeviceItem(main.device_id)
					device_type = device.device_type.value
				else:
					device_type = "Other Device"
				sale.device_type = device_type
				sale.commit()
			except Exception as e:
				sale.device_type = "Unconfirmed"
				print(str(e))

	@staticmethod
	def etl_parts_costs_to_sales():
		api_data = monday.api.get_items_by_board_id(6267736041)  # stock checkout board
		checkout_items = [monday.items.part.StockCheckoutControlItem(_['id'], _) for _ in api_data]
		for ci in checkout_items:
			try:
				main_id = ci.main_item_id.value
				if ci.checkout_line_ids.value:
					line_item_data = monday.api.get_api_items(ci.checkout_line_ids.value)
					line_items = [monday.items.part.StockCheckoutLineItem(_['id'], _) for _ in line_item_data]
					parts_cost = sum(float(_.parts_cost.value) for _ in line_items if _.parts_cost.value)
				else:
					raise Exception(f"No Parts Cost Data Attached for {ci.name}")
				sale_data = monday.items.sales.SaleControllerItem().search_board_for_items(
					"main_item_id", str(main_id)
				)[0]

				sale_item = monday.items.sales.SaleControllerItem(sale_data['id'], sale_data)
				sale_item.parts_cost = parts_cost
				sale_item.commit()
			except Exception as e:
				print(f"Error: {str(e)}")
				ci.etl_to_sale = "f"
				ci.commit()
				continue
