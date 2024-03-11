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


@slack_app.view("stock_count_entry_point")
def show_stock_count_form(ack, body, client):
	log.info('showing stock count form')
	meta = json.loads(body['view']['private_metadata'])

	selected_device_type = \
	body['view']['state']['values']['device_type_select']['stock_count_device_type']['selected_option']['value']
	selected_part_type = \
	body['view']['state']['values']['part_type_select']['stock_count_part_type']['selected_option']['value']

	flow_controller = flows.CountsFlow(slack_client=client, ack=ack, body=body, meta=meta)
	flow_controller.show_stock_count_form(selected_device_type, selected_part_type)
	return True


@slack_app.view("stock_count_form")
def process_stock_count_form_submission(ack, body, client):
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

	return True
