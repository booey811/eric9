import logging

from .blocks import get_modal_base
from .blocks.elements import generate_option, generate_option_groups
from ...models import ProductModel, DeviceModel

log = logging.getLogger('eric')


class DeviceAndProductViews:

	def __init__(self, device: DeviceModel = None, products=[]):
		self._device = device
		self._products = products

		self.view = get_modal_base("Device/Products")
		self.blocks = self.view['blocks']

	@property
	def device(self):
		return self._device

	@device.setter
	def device(self, device_model: DeviceModel):
		self._device = device_model

	@property
	def products(self):
		return self._products

	@products.setter
	def products(self, products: list):
		self._products = products

	def build_view(self):
		log.debug('Building Device/Products view')
		self._build_device_select()
		# self._build_product_select()

		log.debug(self.view)
		return self.view

	def _build_device_select(self):
		devices = DeviceModel.query_all()
		options_dict = {}
		for device in devices:
			options_set = options_dict.get(device.device_type)
			if not options_set:
				options_set = options_dict[device.device_type] = []
			options_set.append((device.name, device.id))

		option_groups = generate_option_groups(options_dict)

		result = {
			"type": "input",
			"block_id": "device_select",
			"label": {
				"type": "plain_text",
				"text": "Select Device",
				"emoji": True
			},
			"element": {
				"type": "static_select",
				"action_id": "device_select",
				"placeholder": {
					"type": "plain_text",
					"text": "Select an item",
					"emoji": True
				},
				"option_groups": option_groups
			}
		}

		if self.device:
			result['element']['initial_option'] = generate_option(
				self.device.name, self.device.id
			)

		self.blocks.append(result)

	def _build_product_select(self, device_id=None):
		options = [
			generate_option(product.name, product.id) for product in ProductModel.query.all()
		]
		option_groups = generate_option_groups(options)
		self.blocks.append({
			"type": "input",
			"block_id": "product_select",
			"label": {
				"type": "plain_text",
				"text": "Select Product",
				"emoji": True
			},
			"element": {
				"type": "static_select",
				"action_id": "product_select",
				"placeholder": {
					"type": "plain_text",
					"text": "Select an item",
					"emoji": True
				},
				"options": option_groups
			}
		})