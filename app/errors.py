class EricError(Exception):
	"""Base error for the application"""

	def __init__(self, message, *args, **kwargs):
		self.message = str(message)

	def __str__(self, *args, **kwargs):
		return self.message


class DataError(EricError):

	def __init__(self, message):
		self.message = message

	def __str__(self):
		return f"DataError: {self.message}"
