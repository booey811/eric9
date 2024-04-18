from ...services.slack import slack_app, blocks, builders, flows
from ...services import monday


@slack_app.action("checks__test")
def test_route_for_checks(ack, body, client):
	ack()
	view = client.views_open(
		trigger_id=body['trigger_id'],
		view=builders.CheckViews.get_loading_screen()
	).data

	MAIN_ID = 6384263114
	main_item = monday.items.MainItem(MAIN_ID)

	flow = flows.ChecksFlow(client, ack, view)
	flow.show_check_form(main_item.device_id, 'cs_walk_pre_check')

	return True
