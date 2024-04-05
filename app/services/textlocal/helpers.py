messages = {
	"Corporate Courier Returned": """Hi {},\n\nThank you for arranging a repair with iCorrect today.\n\nWe can confirm the device has been successfully re-delivered to it's collection point.\n\nPlease do get in touch if you experience any difficulty locating the package.\n\nKind Regards,\n\nThe iCorrect Team\n+442070998517""",

	"Corporate Walk-In Ready to Collect": """Hi {},\n\nThank you for bringing a device into iCorrect for repair.\n\nWe can confirm the repairs have been successfully completed and your device is available for collection at your convenience.\n\nWe shall look forward to seeing you./nKind Regards,\n\nThe iCorrect Team\n+442070998517""",

	"End User Courier Returned": """Hi {},\n\nThank you for arranging to have your device repaired with iCorrect.\n\nWe can confirm your device has been successfully re-delivered to it's collection point.\n\nPlease do get in touch if you experience any difficulty locating the package.\n\nKind Regards,\n\nThe iCorrect Team\n+442070998517""",

	"End User Walk-In Ready to Collect": """Hi {},\n\nThank you for bringing your device into iCorrect for repair.\n\nWe can confirm the repairs have been successfully completed and your device is available for collection at your convenience - we are open between 9am and 6pm Monday to Friday.\n\nWe shall look forward to seeing you.\n\nKind Regards,\n\nThe iCorrect Team\n+442070998517""",

	"End User Walk-In Booking Confirmed": """Hi {},\n\nThank you for booking in to have your device repaired with iCorrect.\n\nShould you experience any isssues in making your appointment, or struggle to find our offices, please don't hesitate to get in contact.\n\nWe shall look forward to seeing you.\n\nKind Regards,\n\nThe iCorrect Team\n+442070998517""",

	"End User Walk-In Diagnostic Received": """Hi {},\n\nThank you for dropping your device off with iCorrect.\n\nWe will aim to get back with you within 24-48 hours.\n\nKind regards,\n\nThe iCorrect Team\n02070998517"""
}


def generate_text_message(main_item):
	def select_string(item):
		try:
			key = f'{item.client.value} {item.service.value} {item.main_status.value}'
			body = messages[key]
		except KeyError:
			try:
				key = f'{item.client.value} {item.service.value} {item.repair_type.value} {item.main_status.value}'
				body = messages[key]
			except KeyError as e:
				raise TextMessageNotWritten(str(e))
		return body

	def format_string(body, item):
		return body.format(item.name.split()[0])

	string = select_string(main_item)
	formatted_string = format_string(string, main_item)
	return formatted_string


def generate_device_prices(product_group, user_first_name):
	selected = [
		'screen',
		'battery',
		'port',
		'housing',
		'camera'
	]

	lines = []

	for item in product_group.products:
		for filter_type in selected:
			if filter_type in item.name.lower():
				lines.append(item.get_fe_title(markdown=False))

	lines_text = '\n'.join(lines)

	device_name = product_group.display_name

	body = f"Hi {user_first_name},\n\nThank you for requesting a price list for the {device_name}. " \
	       f"Please find the prices below:\n\n{lines_text}\n\nShould you wish to book a repair in, please don't " \
	       f"hesitate to get in contact.\n\nKind regards,\n\nThe iCorrect Support Team\n02070998517"

	return body


class TextMessageNotWritten(Exception):
	def __init__(self, text_key):
		self.key = text_key

	def __str__(self):
		return f"text message does not exist: {self.key}"
