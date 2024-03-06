import datetime
import json

from ...services.slack.flows import get_flow
from ...services.slack.exceptions import save_metadata
from ...utilities import notify_admins_of_error
from ...services import monday


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

