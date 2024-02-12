from ....errors import EricError


class MondayError(EricError):

	def __str__(self):
		return f"Monday Error: {str(self.m)}"

	def __init__(self, message):
		self.m = message


class MondayAPIError(MondayError):
	pass


class MondayDataError(MondayError):
	pass
