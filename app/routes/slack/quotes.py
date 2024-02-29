import logging
from pprint import pprint as p
import json
import re

from ...services.slack import slack_app, builders, blocks, helpers, flows
from ...services import monday
from .exceptions import SlackRoutingError

log = logging.getLogger('eric')


@slack_app.command("/test")
def test_modal(ack, client, body):
	ack()
	log.debug("test command ran")
	flow_controller = flows.get_flow('walk_in', client, ack, body)
	view = flow_controller.todays_repairs()
	log.debug(view)
	return True


@slack_app.command("/walk")
def show_todays_walk_in_repairs(ack, client, body):
	log.debug("walk command ran")
	flow_controller = flows.get_flow('walk_in', client, ack, body)
	view = flow_controller.todays_repairs()
	log.debug(view)
	return True


@slack_app.action(re.compile("^view_repair__.*$"))
def show_repair_details(ack, client, body):
	log.debug("view_repair_details ran")
	log.debug(body)
	meta = json.loads(body['view']['private_metadata'])
	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	view = flow_controller.show_repair_details()
	log.debug(view)
	return True


@slack_app.command("/quote")
def show_quote_editor(ack, client, body):
	log.debug("quote command ran")
	modal = builders.blocks.base.get_modal_base(
		"Search for Repair",
		submit=False
	)
	modal['blocks'] = builders.QuoteInformationViews().search_main_board()
	modal['private_metadata'] = json.dumps({'flow': 'adjust_quote'})
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

	loading = client.views_update(
		view_id=body['view']['id'],
		view=builders.ResultScreenViews.get_loading_screen()
	)

	action_id = body['actions'][0]['action_id']
	search_entity = action_id.split('__')[1]

	if search_entity == 'email':
		search_term = body['actions'][0]['value']
		search = monday.items.MainItem(search=True)
		results = search.search_board_for_items('email', search_term)
	elif search_entity == 'ticket':
		search_term = body['actions'][0]['value']
		search = monday.items.MainItem(search=True)
		results = search.search_board_for_items('ticket_id', search_term)

	else:
		raise SlackRoutingError(f"Invalid search_entity for main_board_search action: {search_entity}")

	modal = builders.blocks.base.get_modal_base(
		"Main Board Search",
		cancel='Go Back',
		submit=False
	)
	view_blocks = builders.QuoteInformationViews().main_board_search_results(results)
	modal['blocks'] = view_blocks
	modal['private_metadata'] = body['view']['private_metadata']

	p(modal)
	client.views_update(
		view_id=loading.data['view']['id'],
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


@slack_app.action(re.compile("^edit_quote__.*$"))
def show_quote_editor(ack, body, client):
	log.debug("edit_quote ran")
	log.debug(body)

	meta = json.loads(body['view']['private_metadata'])
	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	view = flow_controller.view_quote()
	log.debug(view)
	return True


@slack_app.action("remove_product")
def remove_product_from_quote(ack, body, client):
	log.debug("remove_product ran")
	log.debug(body)
	product_id = body['actions'][0]['value']

	try:
		meta = json.loads(body['view']['private_metadata'])
	except json.JSONDecodeError:
		raise SlackRoutingError("Invalid private_metadata for remove_product action")

	meta['product_ids'] = [prod for prod in meta['product_ids'] if str(prod) != str(product_id)]

	modal = builders.blocks.base.get_modal_base(
		"Quote Editor",
		submit="Save Changes",
		callback_id=f"edit_quote__{meta['main_id']}"
	)
	modal['blocks'] = builders.QuoteInformationViews().show_quote_editor(meta)
	modal['private_metadata'] = json.dumps(meta)
	client.views_update(
		view_id=body['view']['id'],
		view=modal
	)
	ack()
	return True


@slack_app.action('add_products')
def add_product_to_quote(ack, client, body):
	log.debug("add_products ran")
	log.debug(body)
	meta = json.loads(body['view']['private_metadata'])
	modal = builders.blocks.base.get_modal_base(
		"Select Products",
		cancel="Cancel",
		callback_id="add_products"
	)
	modal['blocks'] = builders.QuoteInformationViews().show_product_selection(meta)
	p(modal)
	modal['private_metadata'] = body['view']['private_metadata']
	client.views_push(
		trigger_id=body["trigger_id"],
		view=modal
	)
	ack()
	return True


@slack_app.action('device_select')
def handle_device_selection(ack, client, body):
	device_id = body['actions'][0]['selected_option']['value']
	meta = json.loads(body['view']['private_metadata'])
	meta['device_id'] = device_id
	meta['product_ids'] = []
	modal = builders.blocks.base.get_modal_base(
		"Select Products",
		cancel="Cancel",
		callback_id="add_products"
	)
	modal['blocks'] = builders.QuoteInformationViews().show_product_selection(meta)
	modal['private_metadata'] = json.dumps(meta)
	client.views_update(
		view_id=body['view']['id'],
		view=modal
	)
	ack()
	return True


@slack_app.view('add_products')
def handle_product_selection_submission(ack, client, body):
	log.debug("product selection view submitted")
	log.debug(body)
	meta = json.loads(body['view']['private_metadata'])
	dct_key = f"product_select__{meta['device_id']}"
	selected_product_ids = [int(_['value']) for _ in
							body['view']['state']['values'][dct_key]['product_select']['selected_options']]
	meta['product_ids'] = selected_product_ids
	modal = builders.blocks.base.get_modal_base(
		"Quote Editor",
		submit="Save Changes",
		callback_id=f'edit_quote__{meta["main_id"]}'
	)
	modal['blocks'] = builders.QuoteInformationViews().show_quote_editor(meta)
	modal['private_metadata'] = json.dumps(meta)
	client.views_update(
		view_id=body['view']['previous_view_id'],
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
