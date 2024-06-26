import json
from typing import List, Union

from ...services import monday
from ...utilities import notify_admins_of_error, users


def update_stock_checkouts(main_id, create_sc_item=False):
	main_item = monday.items.MainItem(main_id).load_from_api()
	profile_status = "Complete"
	try:
		if not main_item.stock_checkout_id.value:
			if not create_sc_item:
				return False
			# make one
			checkout_controller = monday.items.part.StockCheckoutControlItem()
			checkout_controller.main_item_id = str(main_item.id)
			checkout_controller.main_item_connect = [int(main_item.id)]
			checkout_controller.create(main_item.name)
			main_item.stock_checkout_id = str(checkout_controller.id)
			main_item.commit(reload=True)
		else:
			checkout_controller = monday.items.part.StockCheckoutControlItem(main_item.stock_checkout_id.value)
	except Exception as e:
		notify_admins_of_error(f"Could Not Begin Stock Checkout Process: {e}")
		raise e

	# if not main_item.parts_used_dropdown.value:
	# 	checkout_controller.profile_status = "Error"
	# 	checkout_controller.commit()
	# 	checkout_controller.add_update("No Parts Selected")
	# 	return False

	# if not main_item.device_deprecated_dropdown.value:
	# 	checkout_controller.profile_status = "Error"
	# 	checkout_controller.commit()
	# 	checkout_controller.add_update("No Device Selected")
	# 	return False

	try:
		if not main_item.stock_checkout_id.value:
			# make one
			checkout_controller = monday.items.part.StockCheckoutControlItem().create(main_item.name)
			main_item.stock_checkout_id = str(checkout_controller.id)
			main_item.commit()
		else:
			checkout_controller = monday.items.part.StockCheckoutControlItem(main_item.stock_checkout_id.value)

		lines = [monday.items.part.StockCheckoutLineItem(_['id'], _) for _ in
				 monday.api.get_api_items(checkout_controller.checkout_line_ids.value)]

		for line in lines:
			if line.inventory_movement_id.value:
				mov_item = monday.items.part.InventoryAdjustmentItem(line.inventory_movement_id.value)
				mov_item.void_self()
			monday.api.monday_connection.items.delete_item_by_id(line.id)

		# repair_id_lists = main_item.generate_repair_map_value_list()

		# def calculate_parts_from_repair_maps(p_status):
		# 	map_items = []
		# 	for combined_id, dual_id in repair_id_lists:
		# 		comb_id_result = monday.items.part.RepairMapItem.fetch_by_combined_ids(combined_id)
		# 		if comb_id_result:
		# 			map_items.append(comb_id_result[0])
		# 		else:
		# 			dual_id_result = monday.items.part.RepairMapItem.fetch_by_combined_ids(dual_id)
		# 			if dual_id_result:
		# 				map_items.append(dual_id_result[0])
		# 			else:
		# 				# need to create
		# 				blank = monday.items.part.RepairMapItem()
		# 				blank.combined_id = str(combined_id)
		# 				blank.dual_id = str(dual_id)
		#
		# 				d_id, pu_id = dual_id.split("-")
		# 				pu_text = \
		# 					main_item.convert_dropdown_ids_to_labels([pu_id], main_item.parts_used_dropdown.column_id)[
		# 						0]
		# 				device_text = \
		# 					main_item.convert_dropdown_ids_to_labels([d_id],
		# 															 main_item.device_deprecated_dropdown.column_id)[0]
		# 				name = f"{device_text} {pu_text}"
		# 				if main_item.device_colour.value and main_item.device_colour.value != 'Not Selected':
		# 					name = f"{device_text} {pu_text} {main_item.device_colour.value}"
		#
		# 				map_items.append(blank.create(name))
		#
		# 	missing_part_ids = []
		# 	for map_item in map_items:
		# 		if not map_item.part_ids.value:
		# 			missing_part_ids.append(map_item)
		# 		elif len(map_item.part_ids.value) > 1:
		# 			p_status = "User Input Required"
		# 			checkout_controller.add_update(
		# 				f"Multiple Parts Attached to {map_item.name} - User Input Required"
		# 				f"\n\nPlease delete any parts that are not required and set Profile Status to 'Complete'"
		# 			)
		#
		# 	if missing_part_ids:
		# 		urls = [
		# 			f"https://icorrect.monday.com/boards/{monday.items.part.PartItem.BOARD_ID}/pulses/{_.id}" for _ in
		# 			missing_part_ids
		# 		]
		# 		raise monday.api.exceptions.MondayDataError(
		# 			f"No Parts Attached to {len(missing_part_ids)} RepairMaps: {urls}")
		#
		# 	p_ids = []
		# 	for map_item in map_items:
		# 		p_ids.extend(map_item.part_ids.value)
		#
		# 	return p_ids, p_status

		if not main_item.parts_connect.value:
			main_item.main_status = 'Missing Parts Used'
			main_item.commit()
			main_item.add_update(
				"Please indicate which parts you have used by filling in the 'Parts Used' column. If "
				"you have not used any parts, please select 'No Parts Used'",
				main_item.high_level_thread_id.value
			)
			technician = users.User(monday_id=main_item.technician_id.value[0])
			monday.api.monday_connection.items.move_item_to_group(
				main_item.id,
				technician.repair_group_id,
			)
			raise monday.api.exceptions.MondayDataError(
				"No Parts Connected to Main Item, ask the technician in charge of the repair to fill in the 'Parts Used'"
				" column"
			)

		def calculate_parts_from_connect_column(p_status):

			if not main_item.parts_connect.value:
				raise monday.api.exceptions.MondayDataError("No Parts Connected to Main Item")

			p_ids = main_item.parts_connect.value

			return p_ids, p_status

		# part_ids, profile_status = calculate_parts_from_repair_maps(profile_status)
		part_ids, profile_status = calculate_parts_from_connect_column(profile_status)

		parts_data = monday.api.get_api_items(part_ids)
		parts = [monday.items.PartItem(_['id'], _) for _ in parts_data]
		for part in parts:
			i = monday.api.monday_connection.items.create_subitem(
				checkout_controller.id,
				part.name,
			)
			i = monday.items.part.StockCheckoutLineItem(i['data']['create_subitem']['id'], i['data']['create_subitem'])
			i.part_id = str(part.id)
			i.commit()

		checkout_controller.profile_status = profile_status
		if profile_status == "Complete":
			checkout_controller.checkout_status = 'Do Now!'
		checkout_controller.commit()
		return checkout_controller

	except Exception as e:
		notify_admins_of_error(e)
		checkout_controller.profile_status = "Error"
		checkout_controller.commit()
		checkout_controller.add_update(f"Could not setup Stock Checkout: {e}")
		raise e


def process_stock_checkout(stock_checkout_id):
	checkout_controller = monday.items.part.StockCheckoutControlItem(stock_checkout_id).load_from_api()
	try:

		if checkout_controller.profile_status.value != 'Complete':
			raise ValueError(f"Cannot Checkout Stock, Profile Status is not Complete: {checkout_controller}")

		lines = [monday.items.part.StockCheckoutLineItem(_['id'], _) for _ in
				 monday.api.get_api_items(checkout_controller.checkout_line_ids.value)]

		for line in lines:
			if not line.part_id.value:
				notify_admins_of_error(f"Cannot Checkout Stock, Need Part ID: {line}")
				checkout_controller.checkout_status = "Error"
				checkout_controller.add_update(f"Cannot Checkout Stock, Need Part ID: {line}")
				checkout_controller.commit()
				raise ValueError(f"Cannot Checkout Stock, Need Part ID: {line}")
			elif line.line_checkout_status.value == 'Complete':
				message = f"Detected a complete line Item, please regenerate Controller Item: {line}"
				notify_admins_of_error(message)
				checkout_controller.add_update(message)
				checkout_controller.checkout_status = "Error"
				checkout_controller.commit()
				raise monday.api.exceptions.MondayDataError(message)
			part = monday.items.PartItem.get([line.part_id.value])[0]
			mov_item = part.adjust_stock_level(-1, line, 'iCorrect Repairs')
			line.inventory_movement_id = str(mov_item.id)
			line.line_checkout_status = "Complete"
			line.parts_cost = part.supply_price.value
			line.commit()
		checkout_controller.checkout_status = 'Complete'
		checkout_controller.commit()
	except Exception as e:
		message = f"Could Not Checkout Stock Controller {e}"
		notify_admins_of_error(e)
		checkout_controller.checkout_status = 'Error'
		checkout_controller.add_update(message)
		checkout_controller.commit()
		raise e
	return checkout_controller


def process_complete_order_item(order_item_id):
	"""Processes the data from a slack order submission"""
	order_item = monday.items.part.OrderItem(order_item_id)

	try:
		order_lines_data = monday.api.monday_connection.items.fetch_items_by_id(order_item.subitem_ids.value)
		order_lines_data = order_lines_data['data']['items']
		order_lines = [monday.items.part.OrderLineItem(_['id'], _).load_from_api(_) for _ in order_lines_data]

		for line in order_lines:
			try:
				part = monday.items.PartItem(line.part_id.value)
				try:
					if part.supply_price.value:
						current_supply = float(part.supply_price.value)
					else:
						raise Exception("No Supply Price")

					if part.stock_level.value:
						current_stock = int(part.stock_level.value)
					else:
						current_stock = 0

					new_total_stock = current_stock + line.quantity.value

					total_on_hand = current_supply * current_stock
					total_from_line = float(line.price.value) * int(line.quantity.value)
					total = total_on_hand + total_from_line

					new_price = total / new_total_stock
					part.supply_price = new_price
					part.commit()
				except Exception as e:
					line_price = float(line.price.value)
					part.supply_price = line_price
					part.commit()

				part.adjust_stock_level(
					adjustment_quantity=line.quantity.value,
					source_item=order_item,
					movement_type="Order"
				)

				line.processing_status = "Complete"
				line.commit()
			except Exception as e:
				line.processing_status = "Error"
				line.commit()
				raise e

		order_item.order_status = "Complete"
		order_item.commit()
		return order_item

	except Exception as e:
		notify_admins_of_error(f"Could Not Complete Order Processing: {e}")
		order_item.order_status = "Error"
		order_item.commit()
		raise e


def process_completed_count_item(count_item_id):
	count_item = monday.items.counts.CountItem(count_item_id)
	line_item_data = monday.api.get_api_items(count_item.subitem_ids.value)
	line_items = [monday.items.counts.CountLineItem(_['id'], _).load_from_api(_) for _ in line_item_data]

	try:
		for line in line_items:
			try:
				part = monday.items.PartItem(line.part_id.value)
				part.set_stock_level(
					desired_quantity=line.counted.value,
					source_item=line,
					movement_type="Stock Count",
				)
				part.commit()
			except Exception as e:
				notify_admins_of_error(f"Could Not Process Count Line {line}: {e}")
				raise e
			line.adjustment_status = "Complete"
			line.commit()
	except Exception as e:
		notify_admins_of_error(f"Could Not Complete Count Processing: {e}")
		count_item.count_status = "Error"
		count_item.commit()
		raise e
	return count_item


def build_daily_orders():
	suppliers = {}

	item_data = []
	# get auto order parts
	search_results = monday.api.monday_connection.items.fetch_items_by_column_value(
		board_id=monday.items.PartItem.BOARD_ID,
		column_id="status_1",
		value="On"
	)['data']['items_page_by_column_values']

	item_data.extend(search_results['items'])
	while search_results['cursor']:
		search_results = monday.api.monday_connection.items.fetch_items_by_column_value(
			board_id=monday.items.PartItem.BOARD_ID,
			column_id="status_1",
			value="On",
			cursor=search_results['cursor']
		)['data']['items_page_by_column_values']
		item_data.extend(search_results['items'])

	parts = [monday.items.PartItem(_['id'], _).load_from_api(_) for _ in item_data]

	for part in parts:
		if not part.supplier_connect.value:
			supplier_item_id = 6392289150  # 'other' supplier
		else:
			supplier_item_id = part.supplier_connect.value[0]
		supplier_item = suppliers.get(str(supplier_item_id))
		if not supplier_item:
			supplier_item = monday.items.counts.SupplierItem(supplier_item_id).load_from_api()
			suppliers[str(supplier_item_id)] = supplier_item

		add_part_to_order(part, supplier_item)

	return suppliers


def add_part_to_order(part: Union["monday.items.PartItem", str, int], supplier_item=None):
	if isinstance(part, (str, int)):
		part = monday.items.PartItem(part)
		part.load_data()

	if not supplier_item:
		if not part.supplier_connect.value:
			supplier_item_id = 6392289150  # 'other' supplier
		else:
			supplier_item_id = part.supplier_connect.value[0]
		supplier_item = monday.items.counts.SupplierItem(supplier_item_id).load_from_api()

	current_order = supplier_item.current_order

	current_lines = current_order.get_line_items()
	current_part_ids = [str(line.part_id.value) for line in current_lines]
	if str(part.id) in current_part_ids:
		return False

	if part.reorder_level.value:
		reorder_level = int(part.reorder_level.value)
	else:
		reorder_level = 2

	if int(part.stock_level.value) < reorder_level:
		# add to order
		current_order.add_part_to_order(part)

	return current_order


def process_refurb_output_item(refurb_output_id):
	refurb_output = monday.items.part.RefurbOutputItem(refurb_output_id)

	try:
		if not refurb_output.part_id.value:
			raise monday.api.exceptions.MondayDataError(f"{refurb_output} has no Part ID")

		if not refurb_output.batch_size.value:
			raise monday.api.exceptions.MondayDataError(f"{refurb_output} has no Batch Size")

		if refurb_output.parts_movement_id.value:
			mov_item = monday.items.part.InventoryAdjustmentItem(refurb_output.parts_movement_id.value)
			mov_item.void_self()
			refurb_output.parts_movement_id = ""

		part = monday.items.PartItem(refurb_output.part_id.value)

		inv_mov = part.adjust_stock_level(
			adjustment_quantity=refurb_output.batch_size.value,
			source_item=refurb_output,
			movement_type="Refurbished Screen",
		)

		refurb_output.parts_movement_id = str(inv_mov.id)
		refurb_output.parts_adjustment_status = "Complete"
		refurb_output.commit()

	except Exception as e:
		notify_admins_of_error(f"Could Not Process Refurb Output: {e}")
		refurb_output.add_update(f"Could Not Process Refurb Output: {e}")
		refurb_output.parts_adjustment_status = "Error"
		refurb_output.commit()
		raise e

	try:
		list_refurb_components(refurb_output_id, refurb_output)
	except Exception as e:
		notify_admins_of_error(f"Could Not List Refurb Components: {e}")
		raise e


def list_refurb_components(refurb_output_id, refurb_output=None):
	if not refurb_output:
		refurb_output = monday.items.part.RefurbOutputItem(refurb_output_id)
		refurb_output.load_data()

	try:
		part = monday.items.PartItem(refurb_output.part_id.value)
		part.load_from_api()
		if not part.all_refurb_components_connect.value:
			raise monday.api.exceptions.MondayDataError(f"{part.name} has no Refurb Components Connected")
		refurb_component_data = monday.api.get_api_items(part.all_refurb_components_connect.value)
		refurb_components = [monday.items.part.RefurbComponentItem(_['id'], _) for _ in refurb_component_data]
		for component in refurb_components:
			blank = monday.items.part.RefurbOutputSubItem()
			blank.refurb_component_id = str(component.id)
			monday.api.monday_connection.items.create_subitem(
				parent_item_id=refurb_output.id,
				subitem_name=component.name,
				column_values=blank.staged_changes
			)
		refurb_output.refurb_consumption_status = "Waiting for User Input"
		refurb_output.commit()
	except Exception as e:
		refurb_output.refurb_consumption_status = "Error"
		refurb_output.commit()
		refurb_output.add_update(f"Could Not List Refurb Components: {e}")
		raise e


def process_refurb_consumption(refurb_output_id):
	refurb_output = monday.items.part.RefurbOutputItem(refurb_output_id)
	refurb_output.load_data()

	try:
		subitem_data = monday.api.monday_connection.items.fetch_subitems(refurb_output_id)['data']['items'][0]['subitems']
		subitems = [monday.items.part.RefurbOutputSubItem(_['id'], _) for _ in subitem_data]

		for subitem in subitems:
			try:
				if not subitem.quantity_used.value:
					quantity_used = 0
				else:
					quantity_used = -abs(subitem.quantity_used.value)
				refurb_component = monday.items.part.RefurbComponentItem(subitem.refurb_component_id.value)
				refurb_component.load_data()

				inv_mov = refurb_component.adjust_stock_level(
					adjustment_quantity=quantity_used,
					source_item=refurb_output,
					movement_type="Refurb Consumption",
				)

				subitem.movement_item_id = str(inv_mov.id)
				subitem.stock_adjust_status = "Complete"
				subitem.commit()
			except Exception as e:
				subitem.stock_adjust_status = "Error"
				subitem.commit()
				subitem.add_update(f"Could Not Process Refurb Consumption: {e}")
				raise e

		refurb_output.commit()
	except Exception as e:
		refurb_output.refurb_consumption_status = "Error"
		refurb_output.commit()
		refurb_output.add_update(f"Could Not Process Refurb Consumption: {e}")
		raise e


def add_waste_entry(part_id, reason, monday_user_id):
	# first create the waste item, then use this as a source for stock adjustment
	part = monday.items.PartItem(part_id)
	user = users.User(monday_id=monday_user_id)

	try:
		waste_record = monday.items.part.WasteItem()
		waste_record.part_id = str(part_id)
		waste_record.parts_connect = [int(part_id)]
		waste_record.reason = str(reason)
		waste_record.recorded_by = [int(user.monday_id)]
		waste_record.create(part.name)

		waste_record.stock_adjust_status = 'Waste It!'
		waste_record.commit()
	except Exception as e:
		notify_admins_of_error(f"Could Not Process Waste Entry: {e}")
		raise e


def handle_waste_stock_adjustment(waste_id):
	waste_record = monday.items.part.WasteItem(waste_id)

	try:
		waste_record.process_stock_adjustment()
	except Exception as e:
		notify_admins_of_error(f"Could Not Process Waste Stock Adjustment: {e}")
		waste_record.stock_adjust_status = "Error"
		waste_record.commit()
		waste_record.add_update(f"Could Not Process Waste Stock Adjustment: {e}")
		raise e

	waste_record.stock_adjust_status = 'Complete'
	waste_record.commit()

	return waste_record
