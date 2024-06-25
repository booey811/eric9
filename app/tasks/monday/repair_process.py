import datetime

import config
from ...utilities import notify_admins_of_error, users
from ...services import monday as mon_obj, slack


def sync_check_items_and_results_columns(check_item_id=None):
	results_board_id = 6487504495
	results_sub_board_id = 6487518414
	check_board_id = 4455646189

	results_columns = mon_obj.api.boards.get_board(results_sub_board_id)['columns']

	if check_item_id:
		check_items = [mon_obj.items.misc.CheckItem(check_item_id).load_from_api()]
	else:
		# get all the items on the check item board
		item_data = mon_obj.api.get_items_by_board_id(check_board_id)  # Checks Items Board ID
		check_item_data = mon_obj.api.get_api_items([i['id'] for i in item_data])
		check_items = [mon_obj.items.misc.CheckItem(_['id'], _) for _ in check_item_data]

	# for each item, check the results_column_id field
	for check in check_items:
		if not check.results_column_id.value:

			created_col = mon_obj.api.monday_connection.boards.create_column(
				board_id=results_sub_board_id,
				title=check.name,
				column_type='text'
			)

			column_id = created_col['data']['create_column']['id']
			check.results_column_id = str(column_id)
			check.commit()

		else:
			# check if the column exists on the results board
			if check.results_column_id.value not in [col['id'] for col in results_columns]:
				created_col = mon_obj.api.monday_connection.boards.create_column(
					board_id=results_sub_board_id,
					title=check.name,
					column_type='text'
				)
				column_id = created_col['data']['create_column']['id']
				check.results_column_id = str(column_id)
				check.commit()

		# if the column is present, continue
		continue


def request_checks_from_technician(main_item_id, checkpoint_name, monday_user_id=None):
	slack_cli = slack.slack_app.client
	main_item = mon_obj.items.MainItem(main_item_id)
	if monday_user_id or not main_item.technician_id.value:
		user = users.User(monday_id=monday_user_id)
	else:
		monday_user_id = main_item.technician_id.value[0]
		user = users.User(monday_id=monday_user_id)
	device = mon_obj.items.DeviceItem(main_item.device_id)
	timestamp = main_item.repaired_date.value
	if not timestamp:
		timestamp = datetime.datetime.now()
	timestamp = timestamp.strftime("%c")
	if config.get_config().CONFIG == 'DEVELOPMENT':
		user_id = "U038CSWUHLY"
	else:
		user_id = user.slack_id

	# tech pre-checks should only be completed once
	if checkpoint_name == 'tech_pre_check':

		# check whether this checkpoint has already been requested
		check_results_board_query = mon_obj.api.monday_connection.items.fetch_items_by_column_value(
			board_id=mon_obj.items.misc.CheckResultItem.BOARD_ID,
			column_id="text__1",
			value=str(main_item_id)
		)
		if check_results_board_query.get('errors'):
			# no results item found for this repair, proceed with creating a new one
			pass
		elif check_results_board_query['data']['items_page_by_column_values']['items']:
			# results item already exists for this repair, get subitems and check checkpoint names
			subitem_data = mon_obj.api.monday_connection.items.fetch_subitems(
				parent_item_id=check_results_board_query['data']['items_page_by_column_values']['items'][0]['id']
			)
			if subitem_data.get('errors'):
				# subitem retrieval error, proceed with creating a new one
				pass
			elif subitem_data['data']['items'][0]['subitems']:
				for subitem in subitem_data['data']['items']:
					# subitems found, check if this checkpoint has already been requested
					try:
						checkpoint_name_col = [
							col for col in subitem_data['data']['items'][0]['subitems'][0]['column_values'] if
							col['id'] == 'text55__1'
						][0]
						if checkpoint_name_col['text'] == checkpoint_name:
							# checkpoint already requested, do not proceed
							return True
						else:
							# checkpoint not requested, proceed
							pass
					except IndexError:
						# error, create a new one and request checks anyway
						pass

	blocks = [
		slack.blocks.add.simple_text_display(
			text=f"*Check Request:* {main_item.name} _({device.name})_"
		),
		slack.blocks.add.simple_context_block(
			list_of_texts=[timestamp]
		),
		slack.blocks.add.simple_context_block(
			list_of_texts=[checkpoint_name.replace("_", " ").title()]
		),
	]
	blocks.append(slack.blocks.add.actions_block(
		block_elements=[slack.blocks.elements.button_element(
			button_text='Complete Checks',
			action_id='request_checks',
			button_value="test_button",
		)],
	)),

	res = slack_cli.chat_postMessage(
		channel=user_id,
		text=f'Repair Checks Request: {main_item.name}',
		blocks=blocks,
		metadata={
			"event_type": "request_checks",
			"event_payload": {
				"main_id": str(main_item_id),
				"check_point_name": checkpoint_name,
			}
		}
	)

	return res


def print_check_results_main_item(main_item_id, results_subitem_id):
	all_checks = mon_obj.items.misc.CheckItem.get_all()
	main_item = mon_obj.items.MainItem(main_item_id)
	result_data = mon_obj.api.get_api_items([results_subitem_id])[0]
	try:
		timestamp = [col['text'] for col in result_data['column_values'] if col['id'] == 'date__1'][0]
	except IndexError:
		timestamp = "No Timestamp Found"
	checks_with_answers = []
	try:
		results_data = {col['id']: col['text'] for col in result_data['column_values']}
		for col_id in results_data.keys():
			try:
				check_item = [check for check in all_checks if check.results_column_id.value == col_id][0]
			except IndexError:
				continue
			checks_with_answers.append((check_item, results_data[col_id]))

		update = f"==== CHECKS RESULTS ====\n<b>Timestamp:</b> {timestamp}\n"

		for q, a in checks_with_answers:
			positive_response_labels = q.convert_dropdown_ids_to_labels(q.positive_responses.value,
																		q.positive_responses.column_id)
			if not a:
				continue
			if not positive_response_labels:
				a = a
			elif a in positive_response_labels:
				a = f"&#9989; {a}"
			else:
				a = f"&#9940; {a}"
			update += f"\n<b>{q.name}</b>: {a}"

		main_item.add_update(update, main_item.notes_thread_id.value)
		return main_item
	except Exception as e:
		main_item.add_update(f"Could Not Print Device Check Data: {e}", main_item.notes_thread_id.value)
		notify_admins_of_error(f"Could Not Print Device Check Data: {e}")
		raise e
