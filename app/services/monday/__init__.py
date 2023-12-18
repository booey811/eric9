import os

import moncli

moncli.api.api_key = os.environ['MON-SYSTEM']

from ... import EricError


class MondayError(EricError):

	def __str__(self):
		return f"Monday API Error: {str(self.error)}"

	def __init__(self, e):
		self.error = e
