import logging
from pprint import pprint as p

from ...services.slack import slack_app, builders

log = logging.getLogger('eric')


@slack_app.command("/test")
def run_test_function(ack, body, client):
	ack()
	log.debug("test function ran")
	log.debug(body)
	builder = builders.DeviceAndProductView()
	modal = builders.blocks.base.get_modal_base(
		"Test Modal",
	)
	modal['blocks'] = builder.create_device_and_product_blocks()
	p(modal)
	client.views_open(
		trigger_id=body["trigger_id"],
		view=modal
	)
	return True
