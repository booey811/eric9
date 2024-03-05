import abc


class EmailBodyGenerator(abc.ABC):
	"""base class for generating emails, determines interfaces for usage in code"""

	def __init__(self, user):
		self._user = user
		self._email = f"Hi {user.name.split()[0]},\n\n"

	@abc.abstractmethod
	def get_email(self):
		"""returns the email that the generator has produced"""

	def _add_block(self, text_to_add, new_lines=2):
		to_add = f"{text_to_add}"
		for new_line in range(0, new_lines):
			to_add += "\n"

		self._email += f"{to_add}"
