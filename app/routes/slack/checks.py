from ...services.slack import slack_app, blocks, builders, flows
from ...services import monday


@slack_app.action("checks__test")
def test_set_selection(ack, body, client):
	ack()
	view = client.views_open(
		trigger_id=body['trigger_id'],
		view=builders.CheckViews.get_loading_screen()
	).data

	check_set_ids = [
		4347106354,  # iphone
		4347106360,  # ipad
		4347106364,  # macbook
		4347121221,  # watch
		4347122484,  # other
	]

	check_sets = monday.items.misc.PreCheckSet.get(check_set_ids)
	view_blocks = []
	check_set_options = [blocks.objects.option_object(s, str(s.id)) for s in check_sets]

	view_blocks.append(
		blocks.add.input_block(
			block_title="Select Check Set",
			element=blocks.elements.static_select_element(
				action_id="check_set_select",
				options=check_set_options,
				placeholder="Select a check set",
			),
		)
	),

	checkpoint_options = [blocks.objects.option_object(_[0], _[1]) for _ in
						  monday.items.misc.PreCheckSet.AVAILABLE_CHECKPOINTS]

	view_blocks.append(
		blocks.add.input_block(
			block_title="Select Checkpoint",
			element=blocks.elements.static_select_element(
				action_id="device_select",
				placeholder="Select a Checkpoint",
				options=checkpoint_options
			),
		)
	)

	modal = blocks.get_modal_base(
		title="Select Check Set",
		callback_id='checks__test_set_selection',
	)
	modal['blocks'] = view_blocks

	client.views_update(
		view_id=view['view']['id'],
		view=modal
	)
	return True


@slack_app.view("checks__test_set_selection")
def test_route_for_checks(ack, body, client):
	ack({
		"response_action": "update",
		"view": builders.CheckViews.get_loading_screen()
	})

	device_id = 3926515763

	flow = flows.ChecksFlow(client, ack, body)
	flow.show_check_form(device_id, 'tech_post_check')

	return True
