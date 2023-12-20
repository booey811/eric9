from ... import EricError
from .client import client


class MondayError(EricError):

	def __str__(self):
		return f"Monday API Error: {str(self.error)}"

	def __init__(self, e):
		self.error = e
