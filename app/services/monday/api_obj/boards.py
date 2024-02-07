from ..client import client


class BoardCache:
	def __init__(self):
		self._cache = {}

	def get_board(self, board_id):
		board_id = str(board_id)
		if board_id not in self._cache:
			# Fetch the board data here
			# This is a placeholder, replace with your actual implementation
			try:
				self._cache[board_id] = client.boards.fetch_boards_by_id(int(board_id))['data']['boards'][0]
			except IndexError:
				raise ValueError(f"Board with ID {board_id} not found")
		return self._cache[board_id]

	def get_board_column_map(self, board_id):
		board_id = str(board_id)
		board = self.get_board(board_id)
		columns = board['columns']
		column_map = {}
		for column in columns:
			column_map[column['id']] = column['type']
		return column_map


cache = BoardCache()
