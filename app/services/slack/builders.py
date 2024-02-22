import logging
from pprint import pprint as p

from . import blocks, exceptions
from ..monday import items


class DeviceAndProductView:

	def __init__(self, device_id: str | int = 4028854241, product_ids: str | int = []):
		self._device_id = str(device_id)
		self._product_ids = product_ids

		self.blocks = []

		self._device = None
		self._products = None

	@property
	def device(self):
		if not self._device:
			if not self._device_id:
				raise exceptions.SlackDataError("No Device ID Provided, should be impossible")
			self._device = items.DeviceItem(self._device_id)
		return self._device

	@device.setter
	def device(self, device_id: str | int):
		self._device_id = str(device_id)

	@property
	def products(self):
		if not self._products:
			if not self._product_ids:
				raise exceptions.SlackDataError("No Product IDs Provided, should be impossible")
			self._products = [items.ProductItem(pid) for pid in self._product_ids]
		return self._products

	def create_device_and_product_blocks(self):

		results = []

		# add device block
		external_select = blocks.elements.external_select_element(
			action_id="device_select",
			placeholder="Select a device"
		)
		if self.device:
			device_block = blocks.add.input_block(
				block_title="Device",
				element=external_select,
				block_id="device_select",
				initial_option=blocks.objects.generate_option(str(self.device.name), str(self.device.id))
			)
		else:
			device_block = blocks.add.input_block(
				block_title="Device",
				element=external_select,
				block_id="device_select"
			)

		results.append(device_block)

		p(results)
		return results







