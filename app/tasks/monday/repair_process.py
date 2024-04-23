import datetime

import config
from ...utilities import notify_admins_of_error, users
from ...services import monday as mon_obj, slack


def sync_check_items_and_results_columns():
	results_board_id = 6487504495
	results_sub_board_id = 6487518414
	check_board_id = 4455646189

	results_columns = mon_obj.api.boards.get_board(results_sub_board_id)['columns']

	# get all the items on the check item board
	item_data = mon_obj.api.get_items_by_board_id(check_board_id)  # Checks Items Board ID
	check_items = [mon_obj.items.misc.CheckItem(_['id'], _) for _ in item_data]

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


def request_checks_from_technician(main_item_id, checkpoint_name, monday_user_id):
	slack_cli = slack.slack_app.client
	user = users.User(monday_id=monday_user_id)
	main_item = mon_obj.items.MainItem(main_item_id)
	device = mon_obj.items.DeviceItem(main_item.device_id)
	timestamp = main_item.repaired_date.value
	if not timestamp:
		timestamp = datetime.datetime.now()
	timestamp = timestamp.strftime("%c")
	if config.get_config().CONFIG == 'DEVELOPMENT':
		user_id = "U038CSWUHLY"
	else:
		user_id = user.slack_id

	blocks = [
		slack.blocks.add.simple_text_display(
			text=f"*Check Request:* {main_item.name} _({device.name})_"
		),
		slack.blocks.add.simple_context_block(
			list_of_texts=[timestamp]
		)
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
		text=f'Post Check Request: {main_item.name}',
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


def print_results_main_item(main_item_id, results_subitem_id):
	main_item = mon_obj.items.MainItem(main_item_id)
	try:
		raw_col_data = mon_obj.api.monday_connection.boards.fetch_columns_by_board_id(6487518414)['data']['boards'][0][
			'columns']
		col_data = {col['id']: col['title'] for col in raw_col_data}
		raw_results_data = mon_obj.api.get_api_items([results_subitem_id])[0]['column_values']
		results_data = {col['id']: col['text'] for col in raw_results_data}
		results_formatted = [
			(col_data.get(col_id), results_data.get(col_id)) for col_id in results_data.keys()
		]

		update = "==== CHECKS RESULTS ===="
		update += f"\n{results_data['date__1']}\n\n"

		for q, a in results_formatted:
			if q != "Date Submitted" and a:
				update += f"\n<b>{q}</b>: {a}"

		main_item.add_update(update, main_item.notes_thread_id.value)
		return main_item
	except Exception as e:
		main_item.add_update(f"Could Not Print Device Check Data: {e}", main_item.notes_thread_id.value)
		notify_admins_of_error(f"Could Not Print Device Check Data: {e}")
		raise e
