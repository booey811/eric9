from .blocks import get_modal_base
from .blocks.elements import generate_option, generate_option_groups


class DeviceAndProductViews:

	def __init__(self):
		self.slack_data = get_modal_base("Device/Products")
		self.blocks = self.slack_data['view']['blocks']

	def build_view(self):
		pass


