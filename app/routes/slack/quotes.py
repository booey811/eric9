import logging

from ...services.slack import slack_app, builders

log = logging.getLogger('eric')


@slack_app.command("/test")
def run_test_function(ack, body, client):
	ack()
	log.debug("test function ran")
	log.debug(body)
	builder = builders.DeviceAndProductViews()
	view = builder.build_view()
	log.debug(view)
	client.views_open(
		trigger_id=body["trigger_id"],
		view=view
	)
	return True
