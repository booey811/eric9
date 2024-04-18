import logging
from pprint import pprint as p
import json

from . import quotes as slack_quotes, misc, entities, orders, counts, checks
from ...services.slack import slack_app, builders, blocks
from ...services import monday

log = logging.getLogger('eric')


@slack_app.options("device_select")
def device_select_options(ack, body, payload):
	log.debug(body)
	log.debug("device_select_options ran")
	keyword = payload.get("value")
	options = blocks.options.generate_device_options_list(keyword)
	ack(options)
	return True


@slack_app.options("product_select")
def product_select_options(ack, body, payload):
	log.debug(body)
	log.debug("product_select_options ran")

	keyword = payload.get("value")
	meta = json.loads(body['view']['private_metadata'])
	device_id = meta.get("device_id")

	options = blocks.options.generate_product_options(device_id, keyword)

	ack(options)

	return True