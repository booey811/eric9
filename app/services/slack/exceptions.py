from ...errors import EricError


class SlackDataError(EricError):

	def __str__(self):
		return f"Slack Data Error: {self.message}"
