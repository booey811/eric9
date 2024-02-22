import logging
from pprint import pprint as p

from . import quotes as slack_quotes
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