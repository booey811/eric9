import logging

from ...services.slack import slack_app

log = logging.getLogger('eric')


@slack_app.command("/test")
def run_test_function(ack, body):
	ack()
	log.debug("test function ran")
	log.debug(body)
