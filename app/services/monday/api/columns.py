import json
import logging
import abc
from datetime import timezone, datetime
from dateutil import parser as date_parser
import pytz

from .client import conn as monday_connection
from .boards import cache as board_cache
from .exceptions import MondayDataError, MondayAPIError

log = logging.getLogger('eric')


class ValueType(abc.ABC):
	def __init__(self, column_id):
		self.column_id = column_id
		self._value = None

	def __str__(self):
		return str(self._value)

	def __repr__(self):
		return str(self._value)

	@abc.abstractmethod
	def column_api_data(self, search=None):
		raise NotImplementedError

	@abc.abstractmethod
	def load_column_value(self, column_data: dict):
		log.debug(f"Loading column value for {self.column_id}")

	def search_for_board_items(self, board_id, value):
		# search for items on the board with the given value
		# return the item data
		col_data = self.column_api_data(value)
		r = monday_connection.items.fetch_items_by_column_value(board_id, self.column_id, col_data[self.column_id])
		if r.get('data'):
			# success
			items = r['data']['items_page_by_column_values']['items']
			return items
		else:
			raise MondayAPIError(f"Error searching for items with value {value} in column {self.column_id}: {r}")


class TextValue(ValueType):
	def __init__(self, column_id: str):
		super().__init__(column_id)

	@property
	def value(self):
		return self._value

	@value.setter
	def value(self, new_value):
		if isinstance(new_value, str):  # or any other condition you want to check
			self._value = new_value
		else:
			raise ValueError(f"Invalid value: {new_value} ({type(new_value)})")

	def column_api_data(self, search=None):
		# prepare self.value for submission here
		if search:
			value = str(search)
		else:
			value = str(self.value)
		return {self.column_id: value}

	def load_column_value(self, column_data: dict):
		super().load_column_value(column_data)
		try:
			value = column_data['text']
		except KeyError:
			raise InvalidColumnData(column_data, 'text')

		if value is None or value == "":
			# api has fetched a None value, indicating an emtpy column
			value = ""
		else:
			value = str(value)

		log.debug("Loaded column value: %s", value)

		self.value = value
		return self.value


class NumberValue(ValueType):
	def __init__(self, column_id: str):
		super().__init__(column_id)

	@property
	def value(self):
		return self._value

	@value.setter
	def value(self, new_value):
		if isinstance(new_value, (int, float)):  # or any other condition you want to check
			self._value = new_value
		else:
			raise ValueError(f"Invalid value: {new_value} ({type(new_value)})")

	def column_api_data(self, search=None):
		# prepare self.value for submission here
		if search:
			value = search
		else:
			value = self.value
		if isinstance(value, (int, float)):
			return {self.column_id: value}
		else:
			raise ValueError(f"Invalid value: {value} ({type(value)})")

	def load_column_value(self, column_data: dict):
		super().load_column_value(column_data)
		try:
			value = column_data['text']
		except KeyError:
			raise InvalidColumnData(column_data, 'text')

		if value is None or value == "":
			# api has fetched a None value, indicating an emtpy column
			value = 0
		elif isinstance(value, str):
			value = float(value)
		else:
			value = float(value)

		log.debug("Loaded column value: %s", value)
		self.value = value
		return self.value


class StatusValue(ValueType):
	def __init__(self, column_id: str):
		super().__init__(column_id)

	@property
	def value(self):
		return self._value

	@value.setter
	def value(self, new_value):
		if isinstance(new_value, str):  # or any other condition you want to check
			self._value = new_value
		else:
			raise ValueError("Invalid value")

	def column_api_data(self, search=None):
		# prepare self.value for submission here
		if search:
			value = str(search)
		else:
			value = str(self.value)
		return {self.column_id: {"label": value}}

	def load_column_value(self, column_data: dict):
		super().load_column_value(column_data)
		try:
			value = column_data['text']
		except KeyError:
			raise InvalidColumnData(column_data, 'text')

		if value is None or value == "":
			# api has fetched a None value, indicating an emtpy column
			value = ""
		else:
			value = str(value)

		log.debug("Loaded column value: %s", value)

		self.value = value
		return self.value

	def get_label_conversion_dict(self, board_id):
		board = board_cache.get_board(board_id)
		try:
			column = [col for col in board['columns'] if str(col['id']) == str(self.column_id)][0]
		except IndexError:
			raise MondayDataError(f"Column {self.column_id} not found in board {str(board)}")

		formatted_dict = {}
		label_dict = json.loads(column['settings_str'])['labels']
		for key, value in label_dict.items():
			formatted_dict[str(value)] = str(key)
			formatted_dict[str(key)] = str(value)

		return formatted_dict

	def get_label_id(self, board_id, label):
		# get the id of the label with the given name
		label_dict = self.get_label_conversion_dict(board_id)
		try:
			label_id = label_dict[label]
		except KeyError:
			raise MondayDataError(f"Label {label} not found in column {self.column_id} on board {board_id}")
		return label_id

	def get_label_text(self, board_id, label_id):
		# get the text of the label with the given id
		label_dict = self.get_label_conversion_dict(board_id)
		try:
			label_text = label_dict[str(label_id)]
		except KeyError:
			raise MondayDataError(f"Label id {label_id} not found in column {self.column_id} on board {board_id}")
		return label_text


class DateValue(ValueType):
	def __init__(self, column_id: str):
		super().__init__(column_id)

	@property
	def value(self):
		return self._value

	@value.setter
	def value(self, new_value: datetime):
		# make sure it is a datetime in UTC
		if isinstance(new_value, datetime):
			self._value = new_value

		elif new_value is None:
			# allow setting to None, column is cleared
			self._value = None

		else:
			raise ValueError(f"Invalid value: {new_value} ({type(new_value)})")

		log.debug("Set date value: %s", new_value)

	def column_api_data(self, search=None):
		# prepare self.value for submission here
		# desired string format: 'YYYY-MM-DD HH:MM:SS'

		if search:
			value = search
		else:
			value = self.value

		if not value:
			value = ''
		else:
			assert isinstance(value, datetime)
			value = value.astimezone(pytz.utc)
			value = value.strftime('%Y-%m-%d %H:%M:%S')
		return {self.column_id: value}

	def load_column_value(self, column_data: dict):
		super().load_column_value(column_data)
		try:
			value = column_data['text']
		except KeyError:
			raise InvalidColumnData(column_data, 'text')

		if value is None or value == "":
			# api has fetched a None value, indicating an emtpy column
			value = None
		else:
			try:
				col_val_data = json.loads(column_data['value'])
				date = col_val_data.get('date')
				time = col_val_data.get('time')
				if date and time:
					value = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S")
				elif date:
					value = datetime.strptime(date, "%Y-%m-%d")
				else:
					raise ValueError("No date or time data")
				value = value.replace(tzinfo=timezone.utc).astimezone(pytz.timezone("Europe/London"))
			except Exception as e:
				raise ValueError(f"Error parsing date value: {value}")
			assert (isinstance(value, datetime))

		log.debug("Loaded column value: %s", value)

		self.value = value
		return self.value


class LinkURLValue(ValueType):
	def __init__(self, column_id: str):
		super().__init__(column_id)

		self.url = None
		self.text = None

	@property
	def value(self):
		return [self.text, self.url]

	@value.setter
	def value(self, text_and_url: tuple | list):
		if (
				isinstance(text_and_url, (tuple, list))
				and len(text_and_url) == 2
		):
			text, url = text_and_url
			if not text:
				text = None
			if not url:
				url = None
			self.text = text
			self.url = url
		else:
			raise ValueError("Invalid value")

	def column_api_data(self, search=None):
		"""
		create a value to save or searcg the api
		:param search: if search is provided, it will be used instead of self.value
			format of search = [text, url]
		"""
		# prepare self.value for submission here
		if search:
			text, url = search
		else:
			if self.text:
				text = self.text
			else:
				text = ""

			if self.url:
				url = self.url
			else:
				url = ""
		return {self.column_id: {'text': text, 'url': url}}

	def load_column_value(self, column_data: dict):
		super().load_column_value(column_data)
		try:
			value = column_data['text']
		except KeyError:
			raise InvalidColumnData(column_data, 'text')

		if value is None or value == "":
			# api has fetched a None value, indicating an emtpy column
			self.text = None
			self.url = None
		else:
			value = str(value)
			split_value = [str(_.strip()) for _ in value.split("-")]
			if len(split_value) == 2:
				self.text, self.url = split_value
			elif len(split_value) > 2:
				self.text = " - ".join(split_value[:-1])
				self.url = split_value[-1]
			else:
				raise InvalidColumnData(column_data, 'text - url could not be split')

		return self.value


class ConnectBoards(ValueType):
	def __init__(self, column_id: str):
		super().__init__(column_id)

	@property
	def value(self):
		return self._value

	@value.setter
	def value(self, new_ids_list):
		if isinstance(new_ids_list, (list, tuple)):
			# make sure the ids are integers
			try:
				new_ids = [int(_) for _ in new_ids_list]
			except ValueError:
				raise ValueError(f"Invalid value: {new_ids_list}")
			self._value = new_ids
		else:
			raise ValueError(f"Invalid value: {new_ids_list}")

	def column_api_data(self, search=None):
		# prepare self.value for submission here
		# desired format: {col_id: {item_ids: [id1, id2, id3]}}
		if search:
			item_ids = search
		else:
			item_ids = self.value
		return {self.column_id: {"item_ids": item_ids}}

	def load_column_value(self, column_data: dict):
		super().load_column_value(column_data)
		try:
			value_data = column_data['value']
		except KeyError:
			raise InvalidColumnData(column_data, 'value')

		if value_data is None:
			# connected boards column is empty
			linked_ids = []
		else:
			try:
				value_data = json.loads(value_data)
			except json.JSONDecodeError:
				raise InvalidColumnData(column_data, 'json.loads(value)')
			try:
				linked_ids_raw = value_data.get('linkedPulseIds', [])
				linked_ids = [int(_['linkedPulseId']) for _ in list(linked_ids_raw)]
			except Exception as e:
				raise InvalidColumnData(column_data, 'value - linkedPulseIds')

		self.value = linked_ids
		return self.value


class MirroredDataValue(ValueType):
	def __init__(self, column_id: str):
		super().__init__(column_id)
		raise MondayDataError("MirroredDataValue cannot be used yet")

	@property
	def value(self):
		return self._value

	@value.setter
	def value(self, new_value):
		raise ValueError("Cannot set value for a mirrored column")

	def column_api_data(self, search=None):
		raise EditingNotAllowed(self.column_id)

	def load_column_value(self, column_data: dict):
		# this is probably incorrect, but we cannot get values from the API yet so will rewrite when we can
		super().load_column_value(column_data)
		try:
			value = column_data['text']
		except KeyError:
			raise InvalidColumnData(column_data, 'text')

		if value is None or value == "":
			# api has fetched a None value, indicating an emtpy column
			value = ""
		else:
			value = str(value)

		log.debug("Loaded column value: %s", value)

		self.value = value
		return self.value


class LongTextValue(ValueType):
	def __init__(self, column_id: str):
		super().__init__(column_id)

	@property
	def value(self):
		return self._value

	@value.setter
	def value(self, new_value):
		if isinstance(new_value, str):  # or any other condition you want to check
			self._value = new_value
		else:
			raise ValueError("Invalid value")

	def column_api_data(self, search=None):
		# prepare self.value for submission here
		if search:
			value = str(search)
		else:
			value = str(self.value)
		return {self.column_id: value}

	def load_column_value(self, column_data: dict):
		super().load_column_value(column_data)
		try:
			value = column_data['text']
		except KeyError:
			raise InvalidColumnData(column_data, 'text')

		if value is None or value == "":
			# api has fetched a None value, indicating an emtpy column
			value = ""
		else:
			value = str(value)

		log.debug("Loaded column value: %s", value)

		self.value = value
		return self.value


class PeopleValue(ValueType):
	def __init__(self, column_id: str):
		super().__init__(column_id)

	@property
	def value(self):
		return self._value

	@value.setter
	def value(self, new_value):
		if isinstance(new_value, list):  # or any other condition you want to check
			self._value = [int(_) for _ in new_value]
		else:
			raise ValueError(f"Invalid value: {new_value} ({type(new_value)})")

	def column_api_data(self, search: list | tuple = None):
		# prepare self.value for submission here
		if search:
			people_ids = search
		else:
			people_ids = self.value
		str_ids = ", ".join([str(_) for _ in people_ids])
		return {self.column_id: str_ids}

	def load_column_value(self, column_data: dict):
		super().load_column_value(column_data)
		value_data = column_data['value']
		if value_data is None:
			# connected boards column is empty
			people_ids = []
		else:
			try:
				value_data = json.loads(value_data)
			except json.JSONDecodeError:
				raise InvalidColumnData(column_data, 'json.loads(value)')
			try:
				people_ids_raw = value_data.get('personsAndTeams', [])
				people_ids = [int(_['id']) for _ in list(people_ids_raw)]
			except Exception as e:
				raise InvalidColumnData(column_data, 'value - personAndTeams')

		value = people_ids

		log.debug("Loaded column value: %s", value)

		self.value = value
		return self.value


class DropdownValue(ValueType):
	def __init__(self, column_id: str):
		super().__init__(column_id)

		self.ids = []
		self.text_labels = []

	@property
	def value(self):
		return self._value

	@value.setter
	def value(self, new_ids_list):
		if isinstance(new_ids_list, (list, tuple)):
			# make sure the ids are integers
			try:
				new_ids = [int(_) for _ in new_ids_list]
			except ValueError:
				raise ValueError(f"Invalid value (dropdowns can only bet set with ids, not labels): {new_ids_list}")
			self._value = new_ids
		else:
			raise ValueError(f"Invalid value: {new_ids_list}")

	def column_api_data(self, search=None):
		# prepare self.value for submission here
		# desired format: {col_id: {ids: [id1, id2, id3]}}
		if search:
			item_ids = search
		else:
			item_ids = self.value
		return {self.column_id: {"ids": item_ids}}

	def load_column_value(self, column_data: dict):
		super().load_column_value(column_data)
		value_data = column_data['value']
		if value_data is None:
			# connected boards column is empty
			dd_ids = []
		else:
			try:
				value_data = json.loads(value_data)
			except json.JSONDecodeError:
				raise InvalidColumnData(column_data, 'json.loads(value)')
			try:
				dd_ids = value_data.get('ids', [])
			except Exception as e:
				raise InvalidColumnData(column_data, 'value - linkedPulseIds')

		self.value = dd_ids
		return self.value


class CheckBoxValue(ValueType):

	@property
	def value(self):
		return self._value

	@value.setter
	def value(self, value):
		if isinstance(value, bool):
			self._value = value
		else:
			raise ValueError(f"Invalid value: {value}, must be bool")

	def column_api_data(self, search=None):
		if search:
			val = search
		else:
			val = self.value
		return {self.column_id: {'checked': val}}

	def load_column_value(self, column_data: dict):
		super().load_column_value(column_data)
		value_data = json.loads(column_data['value'])

		self.value = value_data['checked']
		return self.value


class TimeTrackingColumn(ValueType):

	@property
	def value(self):
		return self._value

	@value.setter
	def value(self, value):
		raise EditingNotAllowed(self.column_id)

	def column_api_data(self, search=None):
		raise EditingNotAllowed(self.column_id)

	def load_column_value(self, column_data: dict):
		value_data = json.loads(column_data['value'])
		if not value_data.get('duration'):
			return 0
		duration = int(value_data['duration'])
		self._value = duration
		return self._value


class InvalidColumnData(MondayDataError):

	def __init__(self, column_data: dict, key: str):
		super().__init__(f"Invalid column data, no '{key}' value in data: {column_data}")


class EditingNotAllowed(MondayDataError):

	def __init__(self, column_id: str):
		super().__init__(f"Editing not allowed for column {column_id}")
