import logging
from pprint import pprint as p
import json
import re

from ...services.slack import slack_app, builders, blocks, helpers, flows, exceptions
from ...services import monday, zendesk
from ... import tasks
from ...cache.rq import q_low, q_high
from .exceptions import SlackRoutingError

import config

conf = config.get_config()

log = logging.getLogger('eric')


@slack_app.command("/test")
def test_modal(ack, client, body):
	raise Exception("Test Error")


@slack_app.command("/quote")
@slack_app.action("adjust_quote")
def show_quote_search_modal(ack, client, body):
	log.debug("quote command ran")
	flow_controller = flows.get_flow('adjust_quote', client, ack, body)
	flow_controller.quote_search()
	return True


@slack_app.command("/walk")
@slack_app.action("walk_from_home")
def show_todays_walk_in_repairs(ack, client, body):
	log.debug("walk command ran")
	flow_controller = flows.get_flow('walk_in', client, ack, body)
	view = flow_controller.todays_repairs()
	log.debug(view)
	return True


@slack_app.action(re.compile("^load_repair__.*$"))
def fetch_and_show_repair_details(ack, client, body):
	log.debug("load_repair ran")
	log.debug(body)
	main_id = body['actions'][0]['action_id'].split('__')[1]
	loading_screen = client.views_update(
		view_id=body['view']['id'],
		view=builders.ResultScreenViews.get_loading_screen("Fetching Main Board Item.....")
	)
	ack()

	try:
		meta = json.loads(body['view']['private_metadata'])
	except json.JSONDecodeError as e:
		client.views_update(
			view_id=loading_screen.data['view']['id'],
			view=builders.ResultScreenViews.get_error_screen(
				f"An error occurred while getting your metadata\n\n{e}\n\n{body['view']['private_metadata']}")
		)
		return

	if meta['flow'] == 'adjust_quote':
		main_meta = helpers.extract_meta_from_main_item(main_id=main_id)
		meta.update(main_meta)
		flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
		flow_controller.view_quote('push')
		return

	main_id = body['actions'][0]['action_id'].split('__')[1]
	meta = helpers.extract_meta_from_main_item(main_id=main_id)
	meta['flow'] = 'walk_in'
	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	view = flow_controller.show_repair_details(view_id=loading_screen.data['view']['id'])
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


@slack_app.action(re.compile("^user_overflow__.*$"))
def show_user_change_view(ack, client, body):
	log.debug("change_user ran")
	log.debug(body)
	action_id = body['actions'][0]['action_id']
	selected_option = body['actions'][0]['selected_option']['value']
	meta = json.loads(body['view']['private_metadata'])
	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	if selected_option == 'change_user':
		view = flow_controller.change_user('push')
	else:
		raise SlackRoutingError(f"Invalid action_id for user_overflow: {action_id}")
	log.debug(view)
	return True


@slack_app.options("zendesk_user_search")
def generate_zendesk_search_results(ack, body):
	log.debug("zendesk_email_search ran")
	log.debug(body)
	search_term = body['value']
	results = zendesk.helpers.search_zendesk(search_term.lower())
	options = []
	for user in results:
		name = user.name
		email = user.email
		result_name = f"{name} - {email}"[:74]
		options.append(blocks.objects.plain_text_object(text=result_name, value=str(user.id)))
	options.append(blocks.objects.plain_text_object(text="Create New User", value="new_user"))
	ack(options=options)
	return True


@slack_app.action("zendesk_user_search")
def handle_zendesk_user_assignment(ack, body, client):
	log.debug("zendesk_user_search ran")
	log.debug(body)
	user_id = body['actions'][0]['selected_option']['value']
	meta = json.loads(body['view']['private_metadata'])
	if user_id == 'new_user':
		meta['user']['id'] = 'new_user'
		meta['user']['name'] = ''
		meta['user']['email'] = ''
		meta['user']['phone'] = ''
		flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
		view = flow_controller.edit_user('push')
	else:
		user = zendesk.client.users(id=int(user_id))
		meta['user']['id'] = str(user.id)
		meta['user']['name'] = str(user.name)
		meta['user']['email'] = str(user.email)
		meta['user']['phone'] = str(user.phone)
		flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
		view = flow_controller.change_user('update')
	log.debug(view)
	return True


@slack_app.view("change_user")
def handle_user_adjustment(ack, client, body):
	log.debug("change_user view submitted")
	log.debug(body)
	meta = json.loads(body['view']['private_metadata'])
	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	view = flow_controller.show_repair_details('update', view_id=body['view']['root_view_id'])
	log.debug(view)
	return True


@slack_app.action(re.compile("^view_user_overflow__.*$"))
def show_user_details_editor(ack, client, body):
	log.debug("view_user_overflow ran")
	log.debug(body)
	action_id = body['actions'][0]['action_id']
	selected_option = body['actions'][0]['selected_option']['value']
	meta = json.loads(body['view']['private_metadata'])
	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	if selected_option == 'edit_user':
		view = flow_controller.edit_user('push')
	else:
		raise SlackRoutingError(f"Invalid action_id for view_user_overflow: {action_id}")
	log.debug(view)
	return True


@slack_app.view("edit_user")
def handle_user_edit_submission(ack, client, body):
	log.debug("edit_user view submitted")
	log.debug(body)
	user_info = body['view']['state']['values']
	meta = json.loads(body['view']['private_metadata'])
	user_info = {
		'name': user_info['edit_user__name']['edit_user__name']['value'],
		'email': user_info['edit_user__email']['edit_user__email']['value'],
		'phone': user_info['edit_user__phone']['edit_user__phone']['value'],
		'id': meta['user']['id']
	}
	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	flow_controller.handle_user_details_update(new_user_info=user_info)
	return True


@slack_app.action(re.compile("^edit_quote__.*$"))
def show_quote_editor(ack, body, client):
	log.debug("edit_quote ran")
	log.debug(body)

	meta = json.loads(body['view']['private_metadata'])
	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	view = flow_controller.view_quote('push')
	log.debug(view)
	return True


@slack_app.action("imei_sn")
def add_imei_to_metadata(ack, client, body):
	log.debug("imei_sn ran")
	log.debug(body)
	meta = json.loads(body['view']['private_metadata'])
	imei_sn = body['view']['state']['values']['imei_sn']['imei_sn']['value']
	meta['imei_sn'] = imei_sn
	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	flow_controller.show_repair_details('update', view_id=body['view']['id'])
	return True


@slack_app.action("pc")
def add_imei_to_metadata(ack, client, body):
	log.debug("pc ran")
	log.debug(body)
	meta = json.loads(body['view']['private_metadata'])
	pc = body['view']['state']['values']['pc']['pc']['value']
	meta['pc'] = pc
	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	flow_controller.show_repair_details('update', view_id=body['view']['id'])
	return True


@slack_app.action("additional_notes")
def add_imei_to_metadata(ack, client, body):
	log.debug("imei_sn ran")
	log.debug(body)
	meta = json.loads(body['view']['private_metadata'])
	notes = body['view']['state']['values']['additional_notes']['additional_notes']['value']
	meta['additional_notes'] = notes
	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	flow_controller.show_repair_details('update', view_id=body['view']['id'])
	return True


@slack_app.action("remove_product")
def remove_product_from_quote(ack, body, client):
	log.debug("remove_product ran")
	log.debug(body)

	remove_id = body['actions'][0]['value']
	meta = json.loads(body['view']['private_metadata'])
	meta['product_ids'] = [prod for prod in meta['product_ids'] if str(prod) != str(remove_id)]

	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	flow_controller.view_quote(method='update')
	return True


@slack_app.action("remove_custom_product")
def remove_custom_product(ack, body, client):
	log.debug("remove_custom_product ran")
	log.debug(body)

	remove_id = body['actions'][0]['value']
	meta = json.loads(body['view']['private_metadata'])
	meta['custom_products'] = [prod for prod in meta['custom_products'] if str(prod['id']) != str(remove_id)]

	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	flow_controller.view_quote(method='update')
	return True


@slack_app.action('add_products')
def add_product_to_quote(ack, client, body):
	log.debug("add_products ran")
	log.debug(body)
	meta = json.loads(body['view']['private_metadata'])
	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	flow_controller.add_products('push')
	return True


@slack_app.action("add_custom_product")
def add_custom_product_to_quote(ack, client, body):
	log.debug("add_custom_product ran")
	log.debug(body)
	meta = json.loads(body['view']['private_metadata'])
	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	flow_controller.add_custom_product('push')
	return True


@slack_app.view('add_custom_product')
def handle_custom_product_submission(ack, client, body):
	log.debug("custom_product view submitted")
	log.debug(body)
	custom_info = body['view']['state']['values']
	new_custom = {
		'name': custom_info['custom_product_name']['name_input']['value'],
		'price': custom_info['custom_product_price']['price_input']['value'],
		'description': custom_info['custom_product_description']['description_input']['value'],
		'id': 'new_item'
	}

	errors = {}

	try:
		int(new_custom['price'])
	except ValueError:
		errors['custom_product_price'] = "Price must be a number"

	meta = json.loads(body['view']['private_metadata'])
	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	if errors:
		flow_controller.add_custom_product('update', errors=errors, view_id=body['view']['id'])
	else:
		meta['custom_products'].append(new_custom)
		flow_controller.view_quote('update', view_id=body['view']['previous_view_id'])
	return True


@slack_app.action('device_select')
def handle_device_selection(ack, client, body):
	meta = json.loads(body['view']['private_metadata'])
	device_id = body['actions'][0]['selected_option']['value']
	meta['device_id'] = device_id
	meta['product_ids'] = []
	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	flow_controller.add_products('update')
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

	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	flow_controller.view_quote('update', view_id=body['view']['previous_view_id'])
	return True


@slack_app.view('quote_editor')
def handle_quote_editor_submission(ack, client, body):
	log.debug("quote_editor view submitted")
	log.debug(body)
	meta = json.loads(body['view']['private_metadata'])
	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	if meta['flow'] == 'adjust_quote':
		flow_controller.end_flow()
	elif meta['flow'] == 'walk_in':
		flow_controller.show_repair_details('update', view_id=body['view']['previous_view_id'])
	else:
		raise SlackRoutingError(f"Invalid flow for quote_editor: {meta['flow']}")
	return True


@slack_app.action(re.compile("^open_pre_checks__.*$"))
def open_pre_check_menu(ack, client, body):
	log.debug("open_pre_checks ran")
	log.debug(body)
	meta = json.loads(body['view']['private_metadata'])
	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	view = flow_controller.show_pre_check_list()
	log.debug(view)
	return True


@slack_app.view("pre_checks")
def handle_pre_check_submission(ack, client, body):
	log.debug("pre_checks view submitted")
	log.debug(body)
	meta = json.loads(body['view']['private_metadata'])
	pre_check_state_values = body['view']['state']['values']

	for state_val in pre_check_state_values:
		pre_check_data = pre_check_state_values[state_val]
		pre_check_id = list(pre_check_data.keys())[0].split('__')[1]
		pre_check_answer = list(pre_check_data.values())[0]['selected_option']
		if pre_check_answer is None:
			answer = ''
		else:
			answer = pre_check_answer['value']
		meta_check = [i for i in meta['pre_checks'] if str(i['id']) == str(pre_check_id)][0]
		meta_check['answer'] = answer

	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)
	flow_controller.show_repair_details('update', view_id=body['view']['previous_view_id'])
	return True


@slack_app.view("repair_viewer")
def handle_repair_view_submission(ack, client, body):
	log.debug("repair_viewer view submitted")
	log.debug(body)
	meta = json.loads(body['view']['private_metadata'])

	errors = []
	# check pre checks
	for check in meta['pre_checks']:
		if not check['answer']:
			errors.append("Please complete pre-checks before submitting")
			break
	if not meta['pre_checks']:
		errors.append("Please complete pre-checks before submitting")

	flow_controller = flows.get_flow(meta['flow'], client, ack, body, meta)

	if errors:
		flow_controller.show_repair_details('ack', errors=errors, view_id=body['view']['id'])
		return
	else:
		ack()
		if conf.CONFIG == 'development':
			tasks.slack.submissions.process_repair_view_submission(meta)
		else:
			q_high.enqueue(
				f=tasks.slack.submissions.process_repair_view_submission,
				kwargs={'metadata': meta}
			)

	return True


@slack_app.use
def global_view_dump(body, next_):
	log.debug("global view dump")

	try:
		data = body['view']
	except KeyError:
		data = body


	q_high.enqueue(
		f=exceptions.dump_slack_view_data,
		kwargs={"view": data}
	)
	next_()
	return
