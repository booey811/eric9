import json

from ...cache.rq import q_low
from ...services import monday
from ...utilities import notify_admins_of_error


def update_stock_checkouts(main_id, create_sc_item=False):
	main_item = monday.items.MainItem(main_id).load_from_api()
	try:
		if not main_item.stock_checkout_id.value:
			if not create_sc_item:
				return False
			# make one
			checkout_controller = monday.items.part.StockCheckoutControlItem().create(main_item.name)
			main_item.stock_checkout_id = str(checkout_controller.id)
			main_item.commit()
		else:
			checkout_controller = monday.items.part.StockCheckoutControlItem(main_item.stock_checkout_id.value)
	except Exception as e:
		notify_admins_of_error(f"Could Not Begin Stock Checkout Process: {e}")
		raise e

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

		repair_id_lists = main_item.generate_repair_map_value_list()

		map_items = []
		for combined_id, dual_id in repair_id_lists:
			comb_id_result = monday.items.part.RepairMapItem.fetch_by_combined_ids(combined_id)
			if comb_id_result:
				map_items.append(comb_id_result[0])
			else:
				dual_id_result = monday.items.part.RepairMapItem.fetch_by_combined_ids(dual_id)
				if dual_id_result:
					map_items.append(dual_id_result[0])
				else:
					# need to create
					blank = monday.items.part.RepairMapItem()
					blank.combined_id = str(combined_id)
					blank.dual_id = str(dual_id)

					d_id, pu_id = dual_id.split("-")
					pu_text = main_item.convert_dropdown_ids_to_labels([pu_id], main_item.parts_used_dropdown.column_id)[0]
					device_text = \
					main_item.convert_dropdown_ids_to_labels([d_id], main_item.device_deprecated_dropdown.column_id)[0]
					name = f"{device_text} {pu_text}"
					if main_item.device_colour.value and main_item.device_colour.value != 'Not Selected':
						name = f"{device_text} {pu_text} {main_item.device_colour.value}"

					map_items.append(blank.create(name))

		missing_part_ids = []
		for map_item in map_items:
			if not map_item.part_ids.value:
				missing_part_ids.append(map_item)

		if missing_part_ids:
			raise monday.api.exceptions.MondayDataError(f"No Parts Attached to RepairMaps: {missing_part_ids}")

		part_ids = [_.part_ids.value[0] for _ in map_items]
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

		checkout_controller.commit()
		q_low.enqueue(
			process_stock_checkout,
			checkout_controller.id
		)
		return checkout_controller

	except Exception as e:
		notify_admins_of_error(e)
		checkout_controller.checkout_status = "Error"
		checkout_controller.commit()
		checkout_controller.add_update(f"Could not setup Stock Checkout: {e}")
		raise e


def process_stock_checkout(stock_checkout_id):
	checkout_controller = monday.items.part.StockCheckoutControlItem(stock_checkout_id).load_from_api()
	try:
		lines = [monday.items.part.StockCheckoutLineItem(_['id'], _) for _ in monday.api.get_api_items(checkout_controller.checkout_line_ids.value)]

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
	except Exception as e:
		message = f"Could Not Checkout Stock Controller {e}"
		notify_admins_of_error(e)
		checkout_controller.checkout_status = 'Error'
		checkout_controller.add_update(message)
		checkout_controller.commit()
		raise e
	return checkout_controller

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
