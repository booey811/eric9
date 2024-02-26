from ...errors import EricError

class SlackRoutingError(EricError):

	def __str__(self):
		return f"Slack Routing Error: {self.message}"