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
		"""fetches all items on the sales board and updates the device type"""
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
		"""fetches all items on the stock checkouts board and updates the parts cost in the sales board"""
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

	@staticmethod
	def extract_historic_supply_price_to_parts():
		"""fetches all parts that have a supply price of exactly one (should never happen in practice)
		and sets the supply price to the supply price of the last recevied order"""

		parts_search = monday.items.PartItem().search_board_for_items(
			"supply_price", 1
		)
		parts_with_bad_supply_price_query = monday.api.monday_connection.items.fetch_items_by_column_value(
			monday.items.part.PartItem.BOARD_ID,
			"supply_price",
			1
		)

		while parts_with_bad_supply_price_query['data']['items_page_by_column_values']['items']:
			parts_with_bad_supply_price = [monday.items.PartItem(_['id'], _) for _ in parts_with_bad_supply_price_query['data']['items_page_by_column_values']['items']]
			for part in parts_with_bad_supply_price:
				print(f"Processing {part.name}")
				try:
					last_order_query = monday.api.monday_connection.items.fetch_items_by_column_value(
						monday.items.part.OrderLineItem.BOARD_ID,
						"text",
						str(part.id),
						limit=1,
					)
					last_order_data = last_order_query.get('data')
					if last_order_data:
						print(f"Got {len(last_order_data['items_page_by_column_values']['items'])} Order Lines")
						if last_order_data['items_page_by_column_values']['items']:
							item_data = last_order_data['items_page_by_column_values']['items'][0]
							order_line = monday.items.part.OrderLineItem(item_data['id'], item_data)
							print(f"Setting Supply Price to {order_line.price.value}")
							part.supply_price = order_line.price.value
							part.commit()

				except Exception as e:
					print(f"Error: {str(e)}")

			if not parts_with_bad_supply_price_query['data']['items_page_by_column_values']['cursor']:
				break

			parts_with_bad_supply_price_query = monday.api.monday_connection.items.fetch_items_by_column_value(
				monday.items.part.PartItem.BOARD_ID,
				"supply_price",
				1,
				cursor=parts_with_bad_supply_price_query['data']['items_page_by_column_values']['cursor']
			)

	@staticmethod
	def update_sales_parts_costs(sales: list = None):
		"""given items from the sales board, fetch the current supply price of the parts used and update the
		parts cost column in the sales board"""
		if not sales:
			api_data = monday.api.get_items_by_board_id(6285416596)
			sales = [monday.items.sales.SaleControllerItem(_['id'], _) for _ in api_data]
		print(f"Got {len(sales)} sales to process")
		for sale in sales:
			print(f"Processing Sale {sale.name}")
			try:
				thinking = []
				main_id = sale.main_item_id.value
				sc_search = monday.items.part.StockCheckoutControlItem().search_board_for_items(
					"main_item_id", str(main_id)
				)
				if not sc_search:
					raise Exception(f"No Stock Checkout Item Found for {sale.name}")
				sc_id = sc_search[0]['id']
				sc_subitem_query = monday.api.monday_connection.items.fetch_subitems(
					sc_id
				)
				sc_subitem_data = sc_subitem_query['data']['items'][0]['subitems']
				sc_subitems = [monday.items.part.StockCheckoutLineItem(_['id'], _) for _ in sc_subitem_data]
				part_ids = [_.part_id.value for _ in sc_subitems]
				part_data = monday.api.get_api_items(part_ids)
				parts = [monday.items.part.PartItem(_['id'], _) for _ in part_data]
				for _ in parts:
					thinking.append(f"{_.name} has supply price £{_.supply_price.value}")
				parts_cost = sum(float(_.supply_price.value) for _ in parts if _.supply_price.value)
				print(f"Setting Parts Cost: {parts_cost}")
				sale.parts_cost = parts_cost
				sale.commit()
				update = "\n".join(thinking)
				sale.add_update(update)
			except Exception as e:
				print(f"Error: {str(e)}")
				continue