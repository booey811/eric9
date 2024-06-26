import datetime
import json

from ...services.slack.flows import get_flow
from ...services.slack.exceptions import save_metadata
from ...utilities import notify_admins_of_error
from ...services import monday
from ...services.slack import flows


def process_repair_view_submission(metadata):
	"""Processes the data from a repair view submission"""

	flow_controller = get_flow(metadata['flow'], None, None, None, metadata)
	flow_controller.end_flow()


def process_slack_order_submission(metadata):
	"""Processes the data from a slack order submission"""
	try:
		order_item = monday.items.part.OrderItem()
		order_item.app_meta = json.dumps(metadata)
		order_time = datetime.datetime.now().timestamp()
		order_item.create(f"Order {order_time}")
	except Exception as e:
		save_metadata(metadata, "order_submission_error")
		notify_admins_of_error(e)
		raise e

	try:
		for order_line in metadata['order_lines']:

			order_line_item = monday.items.part.OrderLineItem()

			order_line_item.part_id = str(order_line['part_id'])
			order_line_item.quantity = int(order_line['quantity'])
			order_line_item.price = round(float(order_line['price']), 3)
			order_line_item.processing_status = "Pending"

			order_line_item_raw = monday.api.monday_connection.items.create_subitem(
				parent_item_id=order_item.id,
				subitem_name=order_line['name'],
				column_values=order_line_item.staged_changes
			)

		order_item.order_status = 'Submitted'
		order_item.commit()

	except Exception as e:
		order_item.order_status = 'Error'
		order_item.commit()
		notify_admins_of_error(f"Could Not Submit Order: {e}")
		raise e

	return order_item


def process_slack_stock_count(metadata, view=''):

	name = f"Stock Count: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
	count_item = monday.items.counts.CountItem().create(name)

	if view:
		count_item.view_data = json.dumps(view)

	count_item.app_meta = json.dumps(metadata)
	count_item.commit()

	try:

		for count_line in metadata['count_lines']:
			part = monday.items.part.PartItem(count_line['part_id'])
			count_line_item = monday.api.monday_connection.items.create_subitem(count_item.id, part.name)
			count_line_item = monday.items.counts.CountLineItem(count_line_item['data']['create_subitem']['id'])
			try:
				try:
					count_line_item.supply_price = round(part.supply_price.value, 2)
				except TypeError:
					pass
				count_line_item.part_id = count_line['part_id']
				count_line_item.counted = int(count_line['counted'])
				count_line_item.expected = int(part.stock_level.value)

				count_line_item.commit()
			except Exception as e:
				notify_admins_of_error(f"Error creating count line item: {e}")
				count_line_item.add_update(f"Error creating count line item: {e}")
				raise e
		count_item.count_status = "Counted"
		count_item.commit()
	except Exception as e:
		notify_admins_of_error(f"Error processing stock count: {e}")
		count_item.add_update(f"Error processing stock count: {e}")
		count_item.count_status = "Error"
		count_item.commit()
		raise e
	return count_item


def process_check_submission(main_id, submission_values, checkpoint_name):
	"""Processes the data from a check submission"""

	flow = flows.ChecksFlow
	flow.process_submission_data(
		main_id=main_id,
		submission_values=submission_values,
		checkpoint_name=checkpoint_name
	)
	return True
