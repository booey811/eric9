import json
import logging
import re

from ...services.slack import slack_app, blocks, flows
from ...services import monday

log = logging.getLogger('eric')


@slack_app.action("receive_order")
def open_order_build_menu(ack, body, client):
	log.debug("receive_order ran")
	log.debug(body)
	flow_controller = flows.OrderFlow(client, ack, body)
	flow_controller.show_order_menu(method='open')
	return True


@slack_app.options("order_part_search")
def search_parts_for_order(ack, body):
	log.debug("part_search ran")
	log.debug(body)
	search_term = body['value']

	part_options = blocks.options.create_slack_friendly_parts_options(search_term)

	ack(options=part_options)
	return True


@slack_app.action("order_part_search")
def open_add_order_line_menu(ack, body, client):
	log.debug("order_part_search ran")
	log.debug(body)
	meta = json.loads(body['view']['private_metadata'])
	part_id = body['actions'][0]['selected_option']['value']
	if str(part_id) in [_['part_id'] for _ in meta['order_lines']]:
		flow_controller = flows.OrderFlow(client, ack, body, meta)
		flow_controller.show_order_menu(errors={'part_id': 'Part already in order'}, method='update')
		return
	part = monday.items.PartItem.get([part_id])[0]
	meta['current_line'] = flows.OrderFlow.get_order_line_meta(name=part.name, part_id=part.id)
	flow_controller = flows.OrderFlow(client, ack, body, meta)
	flow_controller.show_add_order_line_menu(meta['current_line'], method='push')
	return True


@slack_app.action("costing_method")
def set_costing_method(ack, body, client):
	log.debug("costing_method ran")
	log.debug(body)
	costing_method = body['actions'][0]['selected_option']['value']
	meta = json.loads(body['view']['private_metadata'])
	flow_controller = flows.OrderFlow(client, ack, body, meta)
	flow_controller.show_add_order_line_menu(meta['current_line'], cost_method=costing_method, method='update')
	return True


@slack_app.view("add_order_line")
def handle_adding_order_line(ack, body, client):
	log.debug("add_order_line ran")
	log.debug(body)
	meta = json.loads(body['view']['private_metadata'])
	order_line = meta['current_line']

	errors = {}
	quantity_input = body['view']['state']['values']['quantity_input']['quantity_input']['value']
	price_input = body['view']['state']['values']['price_input']['price_input']['value']
	cost_method = body['view']['state']['values']['costing_method']['costing_method']['selected_option']['value']

	price = quantity = None
	try:
		quantity = int(quantity_input)
	except ValueError:
		errors['quantity_input'] = 'Must be a number'

	try:
		price = round(float(price_input), 3)
	except ValueError:
		errors['price_input'] = 'Must be a number'

	if errors:
		flow_controller = flows.OrderFlow(client, ack, body, meta)
		flow_controller.show_add_order_line_menu(order_line, errors=errors, method='ack')
		return

	if cost_method == 'unit':
		price = price
	elif cost_method == 'total':
		price = round(price / quantity, 3)

	order_line = flows.OrderFlow.get_order_line_meta(
		name=order_line['name'], quantity=quantity, price=price, part_id=order_line['part_id']
	)

	meta['order_lines'].append(order_line)
	meta['current_line'] = {}
	flow_controller = flows.OrderFlow(client, ack, body, meta)
	flow_controller.show_order_menu(method='update', view_id=body['view']['previous_view_id'])
	return True


@slack_app.action(re.compile("^remove_order_line__.*$"))
def remove_order_line_from_order(ack, body, client):
	log.debug("remove_order_line ran")
	log.debug(body)
	part_id = body['actions'][0]['action_id'].split('__')[1]
	meta = json.loads(body['view']['private_metadata'])
	meta['order_lines'] = [_ for _ in meta['order_lines'] if str(_['part_id']) != str(part_id)]
	flow_controller = flows.OrderFlow(client, ack, body, meta)
	flow_controller.show_order_menu(method='update', view_id=body['view']['previous_view_id'])
	return True