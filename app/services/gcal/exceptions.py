from ...errors import EricError


class GCalAPIError(EricError):

	def __str__(self):
		return f"GCal Returned A HTTP Error: {str(self.message)}"
