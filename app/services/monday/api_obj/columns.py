import abc

from ..client import client
from .boards import cache as board_cache


def number_value(column_id, value):
	column_id = str(column_id)
	try:
		value = int(value)
	except ValueError:
		raise ValueError(f"Invalid value for number column: {value}")
	return {
		column_id: value
	}


# class ColumnValueHandler:
# 	def __init__(self, board_id):
# 		self.board_id = board_id
# 		self.board_columns = self.get_board_columns()
#
# 	def get_board_columns(self):
# 		# Fetch the board columns here
# 		# This is a placeholder, replace with your actual implementation
# 		return board_cache.get_board(self.board_id)['columns']
#
# 	def get_item_column_values(self, item_id):
# 		# Fetch the item column values here
# 		# This is a placeholder, replace with your actual implementation
# 		return client.items.fetch_items_by_id([item_id])
#
# 	def match_and_instantiate(self, item_id):
# 		item_column_values = self.get_item_column_values(item_id)
# 		for item_column in item_column_values:
# 			for board_column in self.board_columns:
# 				if item_column['id'] == board_column['id']:
# 					# Match found, now instantiate the correct class based on the type
# 					column_type = board_column['type']
# 					if column_type == 'type1':
# 						return Type1Class(item_column)
# 					elif column_type == 'type2':
# 						return Type2Class(item_column)
# 					# ... and so on for other types


class BaseColumnValue(abc.ABC):

	def __init__(self, column_id, value):
		self.column_id = column_id
		self._value = value

	@property
	def value(self):
		return self._value

	@value.setter
	@abc.abstractmethod
	def value(self, value):
		raise NotImplementedError

	@abc.abstractmethod
	def get_value_change_data(self):
		raise NotImplementedError


class TextColumn(BaseColumnValue):

	def __init__(self, column_id, value=None):
		super().__init__(column_id, value)
		self.column_id = column_id
		self.value = value

	@BaseColumnValue.value.setter
	def value(self, value):
		if isinstance(value, str):
			self._value = value
		else:
			raise ValueError("Value must be a string")

	def get_value_change_data(self):
		column_id = str(self.column_id)
		value = str(self.value)
		return {column_id: value}


class NumberColumn(BaseColumnValue):

	def __init__(self, column_id, value: int = None):
		super().__init__(column_id, value)
		self.column_id = column_id
		self.value = value

	@BaseColumnValue.value.setter
	def value(self, value):
		if isinstance(value, int):
			self._value = value
		elif value is None:
			self._value = None
		else:
			raise ValueError(f"Value must be an integer or None, not {type(value)}")

	def get_value_change_data(self):
		column_id = str(self.column_id)
		value = self._value
		return {column_id: value}


class EricModel:
	@property
	def text_col(self):
		return TextColumn('some_column_id', 'Hello')
