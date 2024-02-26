import logging
from pprint import pprint as p
from typing import List

from . import blocks, exceptions
from ..monday import items


class DeviceAndProductView:

	def __init__(self, meta: dict = None):
		if meta is None:
			meta = {}
		self.meta = meta
		self.blocks = []

		self._device_id = meta.get("device_id")
		self._product_ids = meta.get("product_ids")

		self._device = None
		self._products = None

	def get_meta(self):
		return {
			"device_id": self._device_id,
			"product_ids": self._product_ids
		}

	@property
	def device(self):
		if not self._device:
			if self._device_id:
				self._device = items.DeviceItem(self._device_id)
		return self._device

	@device.setter
	def device(self, device_id: str | int):
		self._device_id = str(device_id)

	@property
	def products(self) -> List[items.ProductItem]:
		if not self._products:
			if not self._product_ids:
				self._products = []
			else:
				self._products = items.ProductItem.get(self._product_ids)
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
				initial_option=[self.device.name, self.device.id],
				dispatch_action=True,
				action_id="device_select"
			)
			results.append(device_block)
			explanation = (
				'Device Items describe all of the devices that we offer repairs for. Connected to each '
				'device is a list of products, or repairs, that we offer for that device. Other pieces of '
				'data are also connected to Devices, such as specifications for the pre-checks that should '
				'be completed when accepting a specific device in')

			text = blocks.objects.text_object(explanation)
			results.append(blocks.add.simple_context_block([text]))

		else:
			device_block = blocks.add.input_block(
				block_title="Device",
				element=external_select,
				block_id="device_select",
				hint='Select a device to explore the entity!',
				dispatch_action=True,
				action_id="device_select"
			)
			results.append(device_block)



		if self.device:
			results.append(blocks.add.simple_text_display("*Related Products*"))
			device_products = [_ for _ in items.ProductItem.fetch_all() if str(_.device_id) == str(self.device.id)]
			for product in device_products:
				overflow_data = [
					[":gear:  View Parts", f"view_parts_{product.id}"],
					[":pound:  Adjust Price", f"adjust_price_{product.id}"],
				]
				overflow_options = [blocks.objects.plain_text_object(_[0], _[1]) for _ in overflow_data]
				overflow_block = blocks.elements.overflow_accessory(f"product_{product.id}", overflow_options)
				product_block = blocks.add.section_block(
					title=f"{product.name}: *£{product.price}*",
					accessory=overflow_block
				)
				results.append(product_block)

		p(results)
		return results
