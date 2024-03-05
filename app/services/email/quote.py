import abc

import zenpy.lib.api_objects

from .base import EmailBodyGenerator


class QuoteEmailGenerator(EmailBodyGenerator):
	"""quote email text generator"""

	def __init__(
			self, user, device,
			product_list: list = (), custom_quote=None, quote_type: str = 'standard'):
		"""

		Parameters
		----------
		user (zenpy.api_obj.User) : Zendesk User Object
		quote_type (str) : one of normal, liquid, power; determines the
		device  : (mon_objects.Device) Eric Device object
		product_list : list of products assigned to the repair (if any)
		custom_quote : custom quote line (if any)
		"""
		super().__init__(user=user)
		if custom_quote is None:
			custom_quote = []
		self._quote_type = quote_type
		self._device = device
		self._products = product_list
		self._custom_quote = custom_quote

	def _insert_intro(self):
		if self._quote_type == 'standard':
			line = f"Thank you for having your {self._device.name} diagnosed by our team."
		elif self._quote_type == 'liquid':
			line = f"Thank you for having your liquid damaged {self._device.name} diagnosed by our team."
		elif self._quote_type == 'power':
			line = f"Thank you for having your {self._device.name} diagnosed by our team, which was showing a power related issue."
		else:
			raise ValueError(f"QuoteEmailGenerator set to incorrect quote_type: {self._quote_type}")

		self._add_block(line)

	def _insert_pre_quote_line(self):
		if self._quote_type == 'standard':
			line = f"We can confirm your {self._device.device_type.value} is repairable, please find your quotation below:"
		elif self._quote_type == 'liquid':
			line = f"Even though your device has had liquid ingress, we can confirm your {self._device.device_type.value} is repairable, please find below your quote:"
		elif self._quote_type == 'power':
			line = f"We can confirm your {self._device.device_type.value} is repairable, please find below your quote for the repairs which will restore your device’s functionality:"
		else:
			raise ValueError(f"QuoteEmailGenerator set to incorrect quote_type: {self._quote_type}")

		self._add_block(line)

	def _insert_product_data(self):

		if self._user.organization:
			corp = True
		else:
			corp = False

		total = 0
		for product in self._products:

			if corp:
				price = round(product.price.value / 1.2, 2)
			else:
				price = round(product.price.value)

			total += price
			self._add_block(f"- {product.name}: £{price}")

		for custom in self._custom_quote:
			if corp:
				price = round(custom.price.value / 1.2, 2)
			else:
				price = round(custom.price.value)

			total += price
			self._add_block(f"- {custom.name}: £{price}")

		if corp:
			total_str = f"TOTAL: £{total} ex VAT"
		else:
			total_str = f"TOTAL: £{total} inc VAT"

		self._add_block(total_str)

	def _insert_turnaround(self):

		longest = 0

		if self._products:
			try:
				from_products = max([int(product.turnaround.value) for product in self._products])
			except ValueError:
				from_products = 0
			longest = max([longest, from_products])

		if self._custom_quote:
			try:
				from_custom = max([int(custom.turnaround.value) for custom in self._custom_quote])
			except ValueError:
				from_custom = 0
			longest = max([longest, from_custom])

		if not longest:
			longest = 24 * 3  # 3 days, as standard

		if longest < 25:  # show time in hours
			line = f"We expect the repair to be completed within {int(longest)} hours of your confirmation."
		else:
			line = f"We expect the repair to be completed within {int(longest / 24)} working days of your confirmation."

		self._add_block(line)

	def _insert_sign_off(self):
		self._add_block(
			"Once we have completed your repair, your device will go through a post repair testing process.")
		self._add_block(
			"Please do advise if you wish for us to proceed with repair, we will add your device to our repair queue.")
		self._add_block("If you have any questions please do not hesitate in letting us know.")
		self._add_block("Kind regards,")

	def get_email(self):
		self._insert_intro()
		self._insert_pre_quote_line()
		self._insert_product_data()
		self._insert_turnaround()
		self._insert_sign_off()
		return self._email
