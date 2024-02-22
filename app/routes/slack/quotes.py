import logging
from pprint import pprint as p
import json

from ...services.slack import slack_app, builders

log = logging.getLogger('eric')


@slack_app.command("/test")
def run_test_function(ack, body, client):
	ack()
	log.debug("test function ran")
	log.debug(body)
	builder = builders.DeviceAndProductView()
	modal = builders.blocks.base.get_modal_base(
		"Test Modal",
	)
	modal['blocks'] = builder.create_device_and_product_blocks()
	modal['private_metadata'] = json.dumps(builder.get_meta())
	client.views_open(
		trigger_id=body["trigger_id"],
		view=modal
	)
	return True


@slack_app.action("device_select")
def handle_device_selection(ack, body, client):
	log.debug("device_select ran")
	log.debug(body)
	selected_device_id = body['actions'][0]['selected_option']['value']
	builder = builders.DeviceAndProductView()
	builder.device = selected_device_id
	modal = builders.blocks.base.get_modal_base(
		"Test Modal",
	)
	modal['blocks'] = builder.create_device_and_product_blocks()
	modal['private_metadata'] = json.dumps(builder.get_meta())
	client.views_update(
		view_id=body['view']['id'],
		view=modal
	)
	ack()
	return True
