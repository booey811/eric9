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


@slack_app.view("checks_form")
def checks_form_submission(ack, body, client):
	# SAMPLE SUBMISSION DATA
	SUB_DATA = {'4455646219': {'check_action__4455646219': {'selected_option': {'text': {'emoji': True,
																						 'text': 'Glass '
																								 'Damage',
																						 'type': 'plain_text'},
																				'value': 'Glass '
																						 'Damage'},
															'type': 'static_select'}},
				'4455646235': {'check_action__4455646235': {'selected_option': {'text': {'emoji': True,
																						 'text': 'Damaged',
																						 'type': 'plain_text'},
																				'value': 'Damaged'},
															'type': 'static_select'}},
				'4455646244': {'check_action__4455646244': {'selected_option': {'text': {'emoji': True,
																						 'text': 'No '
																								 'Damage',
																						 'type': 'plain_text'},
																				'value': 'No '
																						 'Damage'},
															'type': 'static_select'}},
				'4455683287': {'check_action__4455683287': {'selected_option': {'text': {'emoji': True,
																						 'text': 'Blurry '
																								 'Image',
																						 'type': 'plain_text'},
																				'value': 'Blurry '
																						 'Image'},
															'type': 'static_select'}},
				'4455686584': {'check_action__4455686584': {'selected_option': {'text': {'emoji': True,
																						 'text': 'Working',
																						 'type': 'plain_text'},
																				'value': 'Working'},
															'type': 'static_select'}},
				'4455689088': {'check_action__4455689088': {'selected_options': [{'text': {'emoji': True,
																						   'text': 'Not '
																								   'Working',
																						   'type': 'plain_text'},
																				  'value': 'Not '
																						   'Working'}],
															'type': 'multi_static_select'}},
				'4455696563': {'check_action__4455696563': {'selected_option': {'text': {'emoji': True,
																						 'text': 'Below '
																								 '80',
																						 'type': 'plain_text'},
																				'value': 'Below '
																						 '80'},
															'type': 'static_select'}},
				'6437392783': {'check_action__6437392783': {'type': 'plain_text_input',
															'value': '12'}},
				'6437393469': {'check_action__6437393469': {'type': 'number_input',
															'value': '5'}},
				'6437395630': {'check_action__6437395630': {'selected_option': {'text': {'emoji': True,
																						 'text': 'Yes',
																						 'type': 'plain_text'},
																				'value': 'Yes'},
															'type': 'static_select'}},
				'6437398898': {'check_action__6437398898': {'type': 'number_input',
															'value': '12'}},
				'6437587112': {'check_action__6437587112': {'selected_option': {'text': {'emoji': True,
																						 'text': 'No',
																						 'type': 'plain_text'},
																				'value': 'No'},
															'type': 'static_select'}}}

	from pprint import pprint as p

	flow = flows.ChecksFlow(client, ack, body)
	for check_id in body['view']['state']['values']:
		answer = body['view']['state']['values'][check_id]['check_action__' + check_id]['selected_option']['value']

	p(body)
	return True
