from ...services.slack import slack_app, blocks, builders, flows
from ...services import monday


@slack_app.action("checks__test")
def test_route_for_checks(ack, body, client):
	ack()
	view = client.views_open(
		trigger_id=body['trigger_id'],
		view=builders.CheckViews.get_loading_screen()
	).data

	device_id = 3926515763

	flow = flows.ChecksFlow(client, ack, view)
	flow.show_check_form(device_id, 'tech_post_check')

	return True
