from ...services import monday as mon_obj


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

