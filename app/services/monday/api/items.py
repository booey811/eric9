from .columns import ValueType
from .client import MondayAPIError, conn


class BaseItemType:
	BOARD_ID = None

	def __init__(self, item_id=None, api_data: dict = None):
		self.id = item_id

		self.staged_changes = {}

		self._api_data = None
		self._column_data = None
		if api_data:
			self.load_api_data(api_data)

	def __setattr__(self, name, value):
		# Check if the attribute being assigned is an instance of ValueType
		if getattr(self, name, None) and isinstance(getattr(self, name), ValueType):
			getattr(self, name).value = value
			self.staged_changes.update(getattr(self, name).column_api_data())

		# Call the parent class's __setattr__ method
		super().__setattr__(name, value)

	def load_api_data(self, api_data: dict):
		self._api_data = api_data
		self._column_data = api_data['column_values']
		for att in dir(self):
			instance_property = getattr(self, att)
			if isinstance(instance_property, ValueType):
				desired_column_id = instance_property.column_id
				try:
					column_data = [col for col in self._column_data if col['id'] == desired_column_id][0]
				except IndexError:
					raise ValueError(f"Column with ID {desired_column_id} not found in item data")

		self.staged_changes = {}
		return self

	def commit(self, name=None):
		# commit changes to the API
		if not self.id and not name:
			raise ReferenceError("Item ID (of an existing item) or name param must be provided")
		try:
			return conn.items.change_multiple_column_values(
				board_id=self.BOARD_ID,
				item_id=self.id,
				column_values=self.staged_changes
			)
		except Exception as e:
			raise MondayAPIError(f"Error calling monday API: {e}")
