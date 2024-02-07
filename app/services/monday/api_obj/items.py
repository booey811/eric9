import logging

from ..client import client
from .columns import TextColumn, NumberColumn
from .boards import cache as board_cache

log = logging.getLogger('eric')

class EricModel:
	BOARD_ID = None

	def __init__(self, item_id: str | int, item_data: dict):
		self.id = item_id
		self._raw_data = item_data

		self._staged_changes = {}

	def commit_changes(self):
		log.debug(f"Committing changes to item {self.id}")
		log.debug(f"Changes: {self._staged_changes}")
		return client.items.change_multiple_column_values(
			board_id=self.BOARD_ID,
			item_id=self.id,
			column_values=self._staged_changes
		)

	# def add_column(self, column_class, column_id, initial_value=None):
	# 	column_instance = column_class(column_id, initial_value)
	#
	# 	def getter(self):
	# 		return column_instance
	#
	# 	def setter(self, value):
	# 		column_instance.value = value
	# 		self._staged_changes.update(column_instance.get_value_change_data())
	#
	# 	setattr(self.__class__, column_id, property(getter, setter))


class MainModel(EricModel):
	BOARD_ID = 349212843

	def __init__(self, item_id, item_data: dict = None):
		super().__init__(item_id, item_data)

		self._number_value = NumberColumn(column_id="dup__of_quote_total")
		self._text_value = TextColumn(column_id="text69", value='')

	@property
	def number_value(self):
		return self._number_value

	@number_value.setter
	def number_value(self, value):
		assert isinstance(value, int)
		self._number_value.value = value
		self._staged_changes.update(self._number_value.get_value_change_data())

	@property
	def text_value(self):
		return self._text_value

	@text_value.setter
	def text_value(self, value):
		assert isinstance(value, str)
		self._text_value.value = value
		self._staged_changes.update(self._text_value.get_value_change_data())
