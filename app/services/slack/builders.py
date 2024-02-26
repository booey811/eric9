import logging
from pprint import pprint as p
from typing import List

from . import blocks, exceptions
from ..monday import items


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
			part_ids = []
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
				if product.part_ids:
					part_ids.extend(product.part_ids)

			if part_ids:
				parts = items.PartItem.get(part_ids)
				options = [blocks.objects.generate_option(part.name, part.id) for part in parts]
				view_blocks.append(blocks.add.input_block(
					block_title="*View Related Parts*",
					element=blocks.elements.static_select_element("view_part", "Select a part", options=options),
					block_id="view_part",
					dispatch_action=True,
					action_id="view_part",
					hint='Select a part to view more information about it!'
				))

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
