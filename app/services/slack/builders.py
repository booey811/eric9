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
		device_products = device.products
		if device_products:
			part_ids = []
			for prod in device_products:
				if prod.part_ids:
					part_ids.extend(prod.part_ids)
			static_select_element = blocks.elements.static_select_element(
				placeholder="Select a product",
				action_id="product_select",
				options=[blocks.objects.option_object(f"{product.name}: £{product.price}", product.id) for product in
						 device_products]
			)

			static_select_block = blocks.add.input_block(
				block_title="Related Products",
				element=static_select_element,
				block_id="product_select",
				dispatch_action=True,
				action_id="view_product",
				hint='Select a product to view more information about it!'
			)

			view_blocks.append(static_select_block)

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
				view_blocks.append({"type": "divider"})
				parts = items.PartItem.get(part_ids)
				parts.sort(key=lambda x: x.name)
				options = [blocks.objects.option_object(part.name, part.id) for part in parts]
				view_blocks.append(blocks.add.input_block(
					block_title="Related Parts",
					element=blocks.elements.static_select_element("view_part", "Select a part", options=options),
					block_id="view_part",
					dispatch_action=True,
					action_id="view_part",
					hint='Select a part to view more information about it!'
				))
			else:
				view_blocks.append(
					blocks.add.simple_text_display(
						f"No parts are connected to the products for this device, which is odd!"))

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


class QuoteInformationViews:

	@staticmethod
	def quote_selection_view():
		view_blocks = []

		text_input_element = blocks.elements.text_input_element(
			placeholder='Enter an email address',
			action_id="desired_email"
		)

		text_input_block = blocks.add.input_block(
			block_title="Search for a main board item by email",
			element=text_input_element,
			block_id="quote_search",
			dispatch_action=True,
			action_id="main_board_search__email"
		)

		view_blocks.append(text_input_block)

		return view_blocks

	@staticmethod
	def show_products_editor(meta_dict: dict):
		view_blocks = []
		total = 0
		for product in meta_dict['products']:
			overflow_data = [
				[":gear:  Product Info", f"view_product"],
				# [":pound:  Adjust Price", f"adjust_price"],
			]
			overflow_options = [blocks.objects.plain_text_object(_[0], _[1]) for _ in overflow_data]
			overflow_block = blocks.elements.overflow_accessory(f"product_overflow__{product['id']}", overflow_options)
			product_block = blocks.add.section_block(
				title=f"{product['name']}: *£{product['price']}*",
				accessory=overflow_block
			)
			view_blocks.append(product_block)
			total += int(product['price'])

		view_blocks.append(blocks.add.divider_block())
		view_blocks.append(blocks.add.header_block(f"Total: £{total}"))
