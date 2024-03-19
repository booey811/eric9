import os
import urllib.request
import urllib.parse

from . import helpers as messages
from .. import monday


class TextLocalManager:

	def __init__(self):
		self.api_key = os.environ['TEXTLOCAL']

	def _get_message(self, mainboard_item):
		message = messages.generate_text_message(mainboard_item)
		return message

	def _send_text(self, number, message):
		data = urllib.parse.urlencode({'apikey': self.api_key, 'numbers': number,
									   'message': message, 'sender': 'iCorrect'})
		data = data.encode('utf-8')
		request = urllib.request.Request("https://api.txtlocal.com/send/?")
		f = urllib.request.urlopen(request, data)
		return message

	def send_text_notification(self, mainboard_item):
		message = self._get_message(mainboard_item)
		number = mainboard_item.phone.value
		if not number:
			raise NoNumberAvailable(mainboard_item.mon_id)

		self._send_text(number, message)

		return message

	def send_price_list(self, number, product_group, user_name):
		body = messages.generate_device_prices(product_group, user_name)
		self._send_text(number, body)
		return body


class NoNumberAvailable(Exception):

	def __init__(self, main_id):
		self.id = main_id

	def __str__(self):
		return f"https://icorrect.monday.com/boards/349212843/views/51003712/pulses/{self.id}"


def attempt_to_deliver_text_message(main_id):
	main_item = monday.items.MainItem(main_id).load_from_api()
	try:
		return texter.send_text_notification(main_item)
	except Exception as e:
		main_item.add_update(f"Failed to send text message: {e}", main_item.error_thread_id.value)
		return f"Failed to send text message: {e}"


texter = TextLocalManager()
