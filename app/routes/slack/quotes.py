import logging
from pprint import pprint as p
import json
import re

from ...services.slack import slack_app, builders, blocks
from .exceptions import SlackRoutingError

log = logging.getLogger('eric')


@slack_app.command("/test")
def run_test_function(ack, body, client):
	ack()
	log.debug("test function ran")
	log.debug(body)
	builder = builders.DeviceAndProductView()
	modal_blocks = []
	modal_blocks.extend(builder.get_device_select_blocks())
	modal = builders.blocks.base.get_modal_base(
		"Entity Explorer",
	)
	modal['blocks'] = modal_blocks
	modal['private_metadata'] = json.dumps(builder.get_meta())
	p(modal)
	client.views_open(
		trigger_id=body["trigger_id"],
		view=modal
	)
	return True


@slack_app.action('device_info')
@slack_app.action(re.compile("^device_info__.*$"))
def show_device_info(ack, body, client):
	log.debug("device_info ran")
	log.debug(body)
	action_id = body['actions'][0]['action_id']
	if action_id == 'device_info':
		device_id = body['actions'][0]['selected_option']['value']
	elif 'device_info__' in action_id:
		device_id = action_id.split('__')[1]
	else:
		raise SlackRoutingError(f"Invalid action_id for device_info action: {action_id}")

	builder = builders.DeviceAndProductView()
	builder.device = device_id

	modal_blocks = []

	modal = builders.blocks.base.get_modal_base(
		"Device Viewer",
	)

	explanation = (
		'Device Items describe all of the devices that we offer repairs for. Connected to each '
		'device is a list of products, or repairs, that we offer for that device. Other pieces of '
		'data are also connected to Devices, such as specifications for the pre-checks that should '
		'be completed when accepting a specific device in')

	modal_blocks.append(blocks.add.simple_context_block([blocks.objects.text_object(explanation)]))
	modal_blocks.extend(builder.get_device_view())

	modal['blocks'] = modal_blocks
	modal['private_metadata'] = json.dumps(builder.get_meta())
	p(modal)
	client.views_update(
		view_id=body['view']['id'],
		view=modal
	)
	ack()
	return True


@slack_app.action("device_select")
def show_device_info_view(ack, body, client):
	log.debug("device_select ran")
	log.debug(body)
	selected_device_id = body['actions'][0]['selected_option']['value']
	builder = builders.DeviceAndProductView()
	builder.device = selected_device_id

	modal_blocks = []

	modal = builders.blocks.base.get_modal_base(
		"Device Viewer",
	)

	explanation = (
		'Device Items describe all of the devices that we offer repairs for. Connected to each '
		'device is a list of products, or repairs, that we offer for that device. Other pieces of '
		'data are also connected to Devices, such as specifications for the pre-checks that should '
		'be completed when accepting a specific device in')

	modal_blocks.append(blocks.add.simple_context_block([blocks.objects.text_object(explanation)]))
	modal_blocks.extend(builder.get_device_view())

	modal['blocks'] = modal_blocks
	modal['private_metadata'] = json.dumps(builder.get_meta())
	p(modal)
	client.views_update(
		view_id=body['view']['id'],
		view=modal
	)
	ack()
	return True
