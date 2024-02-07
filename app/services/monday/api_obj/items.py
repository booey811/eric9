from ..client import client
from .columns import ValueType, TextValue, NumberValue, StatusValue


class BaseItemType:
	BOARD_ID = None

	def __init__(self, item_id, api_data: dict = None):
		self.id = item_id

		self.staged_changes = {}

		self._api_data = None
		self._column_data = None
		if api_data:
			self.load_column_data(api_data)

	def __setattr__(self, name, value):
		# Check if the attribute being assigned is an instance of ValueType
		if getattr(self, name, None) and isinstance(getattr(self, name), ValueType):
			getattr(self, name).value = value
			self.staged_changes.update(getattr(self, name).column_api_data())

		# Call the parent class's __setattr__ method
		super().__setattr__(name, value)

	def load_item_data(self, api_data: dict):
		self._api_data = api_data
		self._column_data = api_data['column_values']
		for att in dir(self):
			instance_property = getattr(self, att)
			if isinstance(instance_property, ValueType):
				instance_property.value = self._column_data.get(instance_property.column_id)

	def commit(self):
		# commit changes to the API
		return client.items.change_multiple_column_values(
			board_id=self.BOARD_ID,
			item_id=self.id,
			column_values=self.staged_changes
		)
