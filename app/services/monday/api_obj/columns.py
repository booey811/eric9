import abc


class ValueType(abc.ABC):
	def __init__(self, column_id):
		self.column_id = column_id
		self._value = None

	@property
	def value(self):
		return self._value

	@value.setter
	def value(self, new_value):
		self._value = new_value

	def __str__(self):
		return str(self._value)

	def __repr__(self):
		return str(self._value)

	@abc.abstractmethod
	def column_api_data(self):
		raise NotImplementedError


class TextValue(ValueType):
	def __init__(self, column_id: str):
		super().__init__(column_id)

	@ValueType.value.setter
	def value(self, new_value):
		if isinstance(new_value, str):  # or any other condition you want to check
			self._value = new_value
		else:
			raise ValueError("Invalid value")

	def column_api_data(self):
		# prepare self.value for submission here
		value = str(self.value)
		return {self.column_id: value}


class NumberValue(ValueType):
	def __init__(self, column_id: str):
		super().__init__(column_id)

	@ValueType.value.setter
	def value(self, new_value):
		if isinstance(new_value, int):  # or any other condition you want to check
			self._value = new_value
		else:
			raise ValueError("Invalid value")

	def column_api_data(self):
		# prepare self.value for submission here
		value = int(self.value)
		return {self.column_id: value}


class StatusValue(ValueType):
	def __init__(self, column_id: str):
		super().__init__(column_id)

	@ValueType.value.setter
	def value(self, new_value):
		if isinstance(new_value, str):  # or any other condition you want to check
			self._value = new_value
		else:
			raise ValueError("Invalid value")

	def column_api_data(self):
		# prepare self.value for submission here
		value = str(self.value)
		return {self.column_id: {"label": value}}
