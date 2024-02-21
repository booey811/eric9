from ..api.items import BaseItemType
from ..api import columns, exceptions, get_api_items, monday_connection


class RepairPhaseModel(BaseItemType):
	BOARD_ID = 5959544342

	def __init__(self, item_id=None, api_data: dict | None = None, search=False):
		self.products_connect = columns.ConnectBoards("connect_boards")

		self._phase_lines = []

		super().__init__(item_id, api_data, search)

	@property
	def phase_lines(self):
		if not self._phase_lines:
			subitem_data = monday_connection.items.fetch_subitems(self.id)
			lines = [RepairPhaseLine(_['id'], _) for _ in subitem_data['data']['items'][0]['subitems']]
			self._phase_lines = lines.sort(key=lambda x: x.phase_model_index.value)
		return self._phase_lines

	def get_total_minutes_required(self):
		total = 0
		for line in self.phase_lines:
			total += line.required_minutes
		return total


class RepairPhaseLine(BaseItemType):
	BOARD_ID = 5959544342

	def __init__(self, item_id=None, api_data: dict | None = None, search=False):
		self.phase_entity_connect = columns.ConnectBoards("connect_boards")

		self.phase_model_index = columns.NumberValue("numbers5")
		self.minutes_override = columns.NumberValue("numbers")

		self._phase_entity = None
		self._required_minutes = None

		super().__init__(item_id, api_data, search)

	def create(self, name):
		raise Exception("Must use create_subitem method of the monday package")

	@property
	def required_minutes(self):
		if self._required_minutes is None:
			if self.minutes_override.value:
				self._required_minutes = self.minutes_override.value
			else:
				phase_item = self.get_phase_entity_item()
				if phase_item:
					self._required_minutes = phase_item.required_minutes
				else:
					self._required_minutes = 30
		return self._required_minutes

	def get_phase_entity_item(self):
		if self.phase_entity_connect.value:
			return RepairPhaseEntity(self.phase_entity_connect.value[0]).load_from_api()
		else:
			return None


class RepairPhaseEntity(BaseItemType):
	BOARD_ID = 5959721433

	def __init__(self, item_id=None, api_data: dict | None = None, search=False):
		self.phase_lines_connect = columns.ConnectBoards("board_relation")
		self.required_minutes = columns.NumberValue("numbers")
		self.main_board_phase_label = columns.StatusValue("color")

		super().__init__(item_id, api_data, search)

	def get_phase_line_items(self):
		phase_line_ids = self.phase_lines_connect.value
		if phase_line_ids:
			item_data = get_api_items(phase_line_ids)
			return [RepairPhaseLine(_['id'], _) for _ in item_data]
