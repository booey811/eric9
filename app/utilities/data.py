from ..services import monday


def get_board_column_info(board_id, to_console=True):
	board = monday.api.boards.get_board(board_id)
	column_info = {}
	for column in board['columns']:
		column_info[column['id']] = column

	if to_console:
		for key, value in column_info.items():
			print(f"Title: {value['title']}, Type: {value['type']}, Column ID: {key}")

	return column_info
