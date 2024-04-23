import json
import re

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

	main_dev_item_ids = [
		6220566650,  #
		6421161221,
		6346881588,
		6384263114
	]

	main_items = monday.items.MainItem.get(main_dev_item_ids)

	view_blocks = []
	check_set_options = [blocks.objects.option_object(s.name, str(s.id)) for s in main_items]

	view_blocks.append(
		blocks.add.input_block(
			block_title="Select Main Item",
			element=blocks.elements.static_select_element(
				action_id="test_main_item_select",
				options=check_set_options,
				placeholder="Select a main item to check",
			),
		)
	),

	checkpoint_options = [blocks.objects.option_object(_[0], _[0]) for _ in
						  monday.items.misc.PreCheckSet.AVAILABLE_CHECKPOINTS]

	view_blocks.append(
		blocks.add.input_block(
			block_title="Select Checkpoint",
			element=blocks.elements.static_select_element(
				action_id="test_checkpoint_select",
				placeholder="Select a Checkpoint",
				options=checkpoint_options
			),
		)
	)

	modal = blocks.get_modal_base(
		title="Select Check Set",
		callback_id='checks__test_handle_selection',
	)
	modal['blocks'] = view_blocks

	client.views_update(
		view_id=view['view']['id'],
		view=modal
	)
	return True


@slack_app.view("checks__test_handle_selection")
def test_route_for_showing_check_selection(ack, body, client):
	ack({
		"response_action": "update",
		"view": builders.CheckViews.get_loading_screen()
	})

	state_vals = body['view']['state']['values']
	answers = list(state_vals.values())
	main_id = answers[0]['test_main_item_select']['selected_option']['value']
	checkpoint = answers[1]['test_checkpoint_select']['selected_option']['value']

	flow = flows.ChecksFlow(client, ack, body)
	flow.show_check_form(main_id, checkpoint)

	return True


@slack_app.action("request_checks")
def show_checks_form(ack, body, client):
	ack()
	main_id = body['message']['metadata']['event_payload']['main_id']
	checkpoint = body['message']['metadata']['event_payload']['check_point_name']
	external_id = f"checks__{main_id}"
	loading = builders.ResultScreenViews.get_loading_screen('Loading Check Items....')
	loading['external_id'] = external_id
	body = client.views_open(
		trigger_id=body['trigger_id'],
		view=loading)
	flow = flows.ChecksFlow(client, ack, body)
	flow.show_check_form(main_id, checkpoint)
	return True


@slack_app.action(re.compile(r"checks_conditional__(\w+)"))
def adjust_checks_form_from_conditional(ack, body, client):
	meta = json.loads(body['view']['private_metadata'])
	loading = builders.ResultScreenViews.get_loading_screen('Loading Check Items....')
	loading['external_id'] = "checks_conditional_adjustments"
	data = client.views_update(
		view_id=body['view']['id'],
		view=loading
	).data
	conditional_tag = body['actions'][0]['action_id'].split('__')[1]
	answer = body['actions'][0]['selected_option']['value']
	if conditional_tag == 'power':
		if answer == 'Yes':
			conditional = True
		else:
			conditional = False
	else:
		raise ValueError(f"Unknown conditional tag: {conditional_tag}")

	meta['has_power'] = conditional

	flow = flows.ChecksFlow(client, ack, body, meta)
	flow.show_check_form(meta['main_id'], meta['checkpoint_name'], data['view']['id'])
	return True


@slack_app.view("checks_form")
def checks_form_submission(ack, body, client):
	success = builders.ResultScreenViews.get_success_screen("Check Form Submitted! :+1:")
	success['clear_on_close'] = True
	ack({
		"response_action": "update",
		"view": success
	})

	meta = json.loads(body['view']['private_metadata'])

	flow = flows.ChecksFlow(client, ack, body, meta)
	flow.process_submission_data(
		main_id=meta['main_id'],
		submission_values=body['view']['state']['values'],
		checkpoint_name=meta['checkpoint_name']
	)

	return
