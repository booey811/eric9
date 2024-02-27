import logging
from pprint import pprint as p
import json
import re

from ...services.slack import slack_app, builders, blocks
from ...services import monday
from .exceptions import SlackRoutingError

log = logging.getLogger('eric')


@slack_app.command("/quote")
def show_quote_editor(ack, client, body):
	log.debug("quote command ran")
	modal = builders.blocks.base.get_modal_base(
		"Quote Editor",
		submit="Save Quote"
	)
	modal['blocks'] = builders.QuoteInformationViews().search_main_board()
	p(modal)
	client.views_open(
		trigger_id=body["trigger_id"],
		view=modal
	)
	ack()
	return True


@slack_app.action(re.compile("^main_board_search__.*$"))
def search_for_main_board_item(ack, client, body):
	log.debug("main_board_search ran")
	log.debug(body)
	action_id = body['actions'][0]['action_id']
	search_entity = action_id.split('__')[1]

	if search_entity == 'email':
		search_term = body['actions'][0]['value']
		search = monday.items.MainItem(search=True)
		results = search.search_board_for_items('email', search_term)

	else:
		raise SlackRoutingError(f"Invalid search_entity for main_board_search action: {search_entity}")

	modal = builders.blocks.base.get_modal_base(
		"Main Board Search",
		cancel='Go Back'
	)
	view_blocks = builders.QuoteInformationViews().main_board_search_results(results)
	modal['blocks'] = view_blocks

	p(modal)
	client.views_push(
		trigger_id=body["trigger_id"],
		view=modal
	)
	ack()
	return True


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

# @slack_app.action("view_quote")
# def show_quote_editor(ack, client, body):
# 	log.debug("view_quote ran")
# 	log.debug(body)
# 	modal = builders.blocks.base.get_modal_base(
# 		"Quote Editor",
# 		submit="Save Quote"
# 	)
# 	modal['blocks'] = builders.QuoteEditor().build_quote_editor()
# 	client.views_open(
# 		trigger_id=body["trigger_id"],
# 		view=modal
# 	)
# 	ack()
# 	return True
