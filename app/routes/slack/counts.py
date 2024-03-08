import logging
import re
from pprint import pprint as p
import json

from ...services.slack import slack_app, builders, blocks, flows
from ...services import monday
from .exceptions import SlackRoutingError

log = logging.getLogger('eric')


@slack_app.action("start_count")
def show_stock_count_entry_point(ack, client, body):
	log.info('showing stock count entry point')
	flow_controller = flows.CountsFlow(slack_client=client, ack=ack, body=body, meta={})
	flow_controller.show_stock_count_entry_point()
	return True


@slack_app.view("stock_count_entry_point")
def show_stock_count_form(ack, body, client):
	log.info('showing stock count form')
	meta = json.loads(body['view']['private_metadata'])

	selected_device_type = body['view']['state']['values']['device_type_select']['stock_count_device_type']['selected_option']['value']
	selected_part_type = body['view']['state']['values']['part_type_select']['stock_count_part_type']['selected_option']['value']

	flow_controller = flows.CountsFlow(slack_client=client, ack=ack, body=body, meta=meta)
	flow_controller.show_stock_count_form(selected_device_type, selected_part_type)
	return True