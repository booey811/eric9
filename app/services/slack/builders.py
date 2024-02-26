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

	def get_device_select_blocks(self):
		results = []

		device_data = items.DeviceItem.fetch_all(slack_data=True)
		option_groups = blocks.objects.generate_option_groups(device_data)

		static_select = blocks.elements.static_select_element(
			placeholder="Select a device",
			option_groups=option_groups,
			action_id="device_select"
		)

		if self.device:
			device_block = blocks.add.input_block(
				block_title="Device",
				element=static_select,
				block_id="device_select",
				initial_option=[self.device.name, self.device.id],
				dispatch_action=True,
				action_id=f"device_info"
			)
		else:
			device_block = blocks.add.input_block(
				block_title="Device",
				element=static_select,
				block_id="device_select",
				dispatch_action=True,
				action_id=f"device_info"
			)
		results.append(device_block)
		return results

	def get_device_view(self):
		if not self.device:
			raise exceptions.SlackDataError(f"Cannot view Device as no device is set. {self._device_id=}")

		results = [
			blocks.add.header_block(f"{self.device.name}"),
			# blocks.add.simple_text_display(f"*Device Type:* {self.device.device_type.value}")
		]

		device_products = self.device.products
		if device_products:
			results.append(blocks.add.simple_text_display("*Related Products*"))
			for product in device_products:
				overflow_data = [
					[":gear:  View Parts", f"view_parts_{product.id}"],
					[":pound:  Adjust Price", f"adjust_price_{product.id}"],
				]
				overflow_options = [blocks.objects.plain_text_object(_[0], _[1]) for _ in overflow_data]
				overflow_block = blocks.elements.overflow_accessory(f"product_overflow__{product.id}", overflow_options)
				product_block = blocks.add.section_block(
					title=f"{product.name}: *£{product.price}*",
					accessory=overflow_block
				)
				results.append(product_block)

		return results

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


class EntityInformationViews:

	def __init__(self):
		pass

	@staticmethod
	def view_device(device_id):
		view_blocks = []
		device = items.DeviceItem(device_id)
		view_blocks.append(blocks.add.header_block(f"{device.name}"))
		view_blocks.append(blocks.add.simple_text_display(f"*Related Products*"))
		device_products = device.products
		if device_products:
			for product in device_products:
				overflow_data = [
					[":gear:  Product Info", f"view_product"],
					# [":pound:  Adjust Price", f"adjust_price"],
				]
				overflow_options = [blocks.objects.plain_text_object(_[0], _[1]) for _ in overflow_data]
				overflow_block = blocks.elements.overflow_accessory(f"product_overflow__{product.id}", overflow_options)
				product_block = blocks.add.section_block(
					title=f"{product.name}: *£{product.price}*",
					accessory=overflow_block
				)
				view_blocks.append(product_block)
		else:
			view_blocks.append(
				blocks.add.simple_text_display(f"No products are connected to this device, which is odd!"))
		return view_blocks

	@staticmethod
	def view_product(product_id):
		view_blocks = []
		product = items.ProductItem(product_id)
		view_blocks.append(blocks.add.header_block(f"{product.name}"))
		view_blocks.append(blocks.add.simple_text_display(f"*Parts Used for this Product*"))
		if product.part_ids:
			product_parts = items.PartItem.get(product.part_ids)
			for part in product_parts:
				overflow_data = [
					[":gear:  Part Info", f"view_part"],
				]
				overflow_options = [blocks.objects.plain_text_object(_[0], _[1]) for _ in overflow_data]
				overflow_block = blocks.elements.overflow_accessory(f"part_overflow__{part.id}", overflow_options)
				part_block = blocks.add.section_block(
					title=f"{part.name}: {part.stock_level} in stock",
					accessory=overflow_block
				)
				view_blocks.append(part_block)
		return view_blocks

	@staticmethod
	def view_part(part_id):
		view_blocks = []
		part = items.PartItem(part_id)
		view_blocks.append(blocks.add.header_block(f"{part.name}"))
		view_blocks.append(blocks.add.simple_text_display(f"*Stock Level:* {part.stock_level}"))
		return view_blocks

	@staticmethod
	def entity_view_entry_point():
		results = []

		device_data = items.DeviceItem.fetch_all(slack_data=True)
		option_groups = blocks.objects.generate_option_groups(device_data)

		static_select = blocks.elements.static_select_element(
			placeholder="Select a device",
			option_groups=option_groups,
			action_id="device_select"
		)

		device_block = blocks.add.input_block(
			block_title="Device",
			element=static_select,
			block_id="device_select",
			dispatch_action=True,
			action_id=f"device_info"
		)

		results.append(device_block)
		return results
