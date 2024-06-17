import logging
import re
from pprint import pprint as p
import json

from ...services.slack import slack_app, builders, blocks, flows, exceptions
from ...services import monday
from .exceptions import SlackRoutingError
from ...cache.rq import q_low
from ...tasks.slack.submissions import process_slack_stock_count
from ...utilities import notify_admins_of_error

import config

log = logging.getLogger('eric')
conf = config.get_config()


@slack_app.action("start_count")
def show_stock_count_entry_point(ack, client, body):
	log.info('showing stock count entry point')
	flow_controller = flows.CountsFlow(slack_client=client, ack=ack, body=body, meta={})
	flow_controller.show_stock_count_entry_point()
	return True


@slack_app.action("stock_count_device_type")
def show_available_devices_for_stock_count(ack, client, body):
	log.info('showing devices for stock count')
	selected_device_type = body['actions'][0]['selected_option']['value']
	log.debug(f"Selected device type: {selected_device_type}")
	flow_controller = flows.CountsFlow(slack_client=client, ack=ack, body=body, meta={})
	flow_controller.show_stock_count_entry_point(selected_device_type)
	return True


@slack_app.view("stock_count_entry_point")
def show_stock_count_form(ack, body, client):
	log.info('showing stock count form')
	meta = json.loads(body['view']['private_metadata'])

	selected_device_type = \
		body['view']['state']['values']['device_type_select']['stock_count_device_type']['selected_option']['value']
	log.debug(f"Selected device type: {selected_device_type}")
	selected_devices = body['view']['state']['values']['device_select']['stock_count_select_devices']['selected_options']
	selected_device_ids = [device['value'] for device in selected_devices]
	if 'all' in selected_device_ids:
		selected_devices = monday.items.DeviceItem.fetch_all()
		selected_devices = [d for d in selected_devices if selected_device_type.lower() in d.device_type.value.lower()]
		selected_device_ids = [str(device.id) for device in selected_devices]
	log.debug(f"Selected devices: {selected_devices}")
	selected_part_type = \
		body['view']['state']['values']['part_type_select']['stock_count_part_type']['selected_option']['value']
	log.debug(f"Selected part type: {selected_part_type}")

	flow_controller = flows.CountsFlow(slack_client=client, ack=ack, body=body, meta=meta)
	flow_controller.show_stock_count_form(selected_device_ids, selected_part_type)
	return True


@slack_app.view("stock_count_form")
def process_stock_count_form_submission(ack, body):
	log.info('processing stock count form submission')
	meta = json.loads(body['view']['private_metadata'])
	try:
		values = body['view']['state']['values']
		for val_dict in values:
			part_id = val_dict.split('__')[1]

			count = values[val_dict][f"stock_count__{part_id}"]['value']

			count_line = [line for line in meta['count_lines'] if line['part_id'] == part_id][0]
			count_line['counted'] = count
	except Exception as e:
		log.error(f"Error processing stock count form submission: {e}")
		notify_admins_of_error(e)
		q_low.enqueue(
			process_slack_stock_count,
			kwargs={
				"metadata": meta,
				"view": body['view']
			}
		)
		raise SlackRoutingError("Error processing stock count form submission")

	exceptions.save_metadata(meta, "count_form_submission_error")
	ack()
	if conf.CONFIG in ("DEVELOPMENT", "TESTING"):
		process_slack_stock_count(meta)
	else:
		q_low.enqueue(
			process_slack_stock_count,
			kwargs={
				"metadata": meta,
			}
		)
	return True
