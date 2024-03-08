import logging
import re
from pprint import pprint as p

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
