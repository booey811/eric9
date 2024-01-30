class EricError(Exception):
	"""Base error for the application"""


class DataError(EricError):

	def __init__(self, message):
		self.message = message

	def __str__(self):
		return f"DataError: {self.message}"
