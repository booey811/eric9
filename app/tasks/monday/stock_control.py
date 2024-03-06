from ...services import monday
from ...utilities import notify_admins_of_error


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

