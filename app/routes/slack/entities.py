import logging
import re
from pprint import pprint as p

import config

from ...services.slack import slack_app, builders, blocks, flows
from ...tasks.monday import stock_control
from ...utilities import users, notify_admins_of_error
from ...cache.rq import q_low
from .exceptions import SlackRoutingError

log = logging.getLogger('eric')
conf = config.get_config()


@slack_app.command("/entity")
def run_test_function(ack, body, client):
	ack()
	log.debug("entity viewer function ran")
	log.debug(body)
	builder = builders.EntityInformationViews()
	modal = blocks.get_modal_base(
		"Entity Viewer",
		submit=None
	)
	modal['blocks'] = builder.entity_view_entry_point()
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

	builder = builders.EntityInformationViews()

	modal_blocks = []

	modal = builders.blocks.base.get_modal_base(
		"Device Viewer",
	)

	modal_blocks.extend(builder.view_device(device_id))

	modal['blocks'] = modal_blocks
	p(modal)
	client.views_update(
		view_id=body['view']['id'],
		view=modal
	)
	ack()
	return True


@slack_app.action("view_product")
def respond_to_product_overview_selection(ack, client, body):
	log.debug("product_overflow ran")
	log.debug(body)
	action_id = body['actions'][0]['action_id']
	if action_id == 'view_product':
		product_id = body['actions'][0]['selected_option']['value']
	else:
		raise SlackRoutingError(f"Invalid action_id for product_overflow action: {action_id}")

	builder = builders.EntityInformationViews()

	modal_blocks = []
	modal_blocks.extend(builder.view_product(product_id))

	modal = builders.blocks.base.get_modal_base(
		"Product Viewer",
	)
	modal['blocks'] = modal_blocks

	client.views_push(
		trigger_id=body["trigger_id"],
		view=modal
	)
	ack()
	return True


@slack_app.action("view_part")
@slack_app.action(re.compile("^part_overflow__.*$"))
def show_part_info(ack, body, client):
	log.debug("view_part ran")
	log.debug(body)
	action_id = body['actions'][0]['action_id']
	if action_id == 'view_part':
		part_id = body['actions'][0]['selected_option']['value']
	elif action_id.startswith('part_overflow__'):
		part_id = action_id.split('__')[1]
	else:
		raise SlackRoutingError(f"Invalid action_id for show part info action: {action_id}")

	builder = builders.EntityInformationViews()

	modal_blocks = []

	modal = builders.blocks.base.get_modal_base(
		"Part Viewer",
	)

	modal_blocks.extend(builder.view_part(part_id))

	modal['blocks'] = modal_blocks
	p(modal)
	client.views_push(
		trigger_id=body["trigger_id"],
		view=modal
	)
	ack()
	return True


@slack_app.action("check_stock")
def show_stock_check_modal(ack, body, client):
	log.debug("check_stock ran")
	log.debug(body)

	flow_controller = flows.StockFlow(client, ack, body, meta={})

	flow_controller.show_stock_check_menu()
	ack()
	return True


@slack_app.options("stock_check_part")
def return_part_options(ack, body, client):
	log.debug("part_search ran")
	log.debug(body)
	search_term = body['value']

	part_options = blocks.options.create_slack_friendly_parts_options(search_term)

	ack(options=part_options)
	return True


@slack_app.action("stock_check_part")
def stock_check_part_info(ack, body, client):
	log.debug("stock_check_part ran")
	log.debug(body)
	part_id = body['actions'][0]['selected_option']['value']
	flow_controller = flows.StockFlow(client, ack, body, meta={})
	flow_controller.show_stock_info([part_id], method='push')
	return True


@slack_app.action("create_waste_entry")
def create_waste_entry(ack, body, client):
	log.debug("create_waste_entry ran")
	log.debug(body)
	flow_controller = flows.WasteFlow(client, ack, body, meta={})
	flow_controller.show_waste_form()
	return True


@slack_app.view("waste_form")
def process_waste_entry_submission(ack, body, client):
	log.debug("process_waste_entry_submission ran")
	state_values = body['view']['state']['values']
	waste_part_id = state_values['waste_part']['stock_check_part']['selected_option']['value']
	waste_reason = state_values['waste_reason']['waste_reason']['value']
	slack_user_id = body['user']['id']
	try:
		user = users.User(slack_id=slack_user_id)
	except Exception as e:
		ack({
			"response_action": "update",
			"view": builders.ResultScreenViews().get_error_screen(f"Could not find user: {e}")
		})
		notify_admins_of_error(f"Waste Records - Could not find user: {e}")
		raise e

	# ack({
	# 	"response_action": "clear"
	# })

	if conf.CONFIG == 'PRODUCTION':
		q_low.enqueue(
			stock_control.add_waste_entry,
			kwargs={
				"part_id": waste_part_id,
				"reason": waste_reason,
				"monday_user_id": user.monday_id
			}
		)
	else:
		stock_control.add_waste_entry(
			part_id=waste_part_id,
			reason=waste_reason,
			monday_user_id=user.monday_id
		)
	return True
