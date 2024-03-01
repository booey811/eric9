import logging
from pprint import pprint as p
from typing import List

from . import blocks, exceptions
from ..monday import items
from ..zendesk import helpers as zendesk_helpers, client as zendesk_client


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
	def search_main_board():
		view_blocks = []

		email_input_element = blocks.elements.text_input_element(
			placeholder='Enter an email address',
			action_id="desired_email"
		)

		email_input_block = blocks.add.input_block(
			block_title="Search for a main board item by email",
			element=email_input_element,
			block_id="email_search",
			dispatch_action=True,
			action_id="main_board_search__email"
		)

		ticket_input_element = blocks.elements.text_input_element(
			placeholder='Enter a Zendesk Ticket ID',
			action_id="desired_ticket_id"
		)

		ticket_input_block = blocks.add.input_block(
			block_title="Search for a main board item by ticket number",
			element=ticket_input_element,
			block_id="ticket_search",
			dispatch_action=True,
			action_id="main_board_search__ticket"
		)

		view_blocks.append(email_input_block)
		view_blocks.append(ticket_input_block)

		return view_blocks

	@staticmethod
	def main_board_search_results(results: List[dict]):
		view_blocks = []
		if results:
			for result in results:
				item = items.MainItem(result['id'], result)
				name = item.name
				item_id = item.id
				date_received = item.date_received.value
				if date_received:
					date_received = date_received.strftime("%d/%m/%Y")
				else:
					date_received = "No date received"

				button_object = blocks.elements.button_element(
					button_text='View',
					action_id=f"edit_quote__{item_id}",
				)
				view_blocks.append(blocks.add.section_block(
					title=name,
					accessory=button_object,

				))
				view_blocks.append(blocks.add.simple_context_block([f"Date Received: {date_received}"]))
				view_blocks.append(blocks.add.simple_context_block([f"IMEI/SN: {item.imeisn.value}"]))
				view_blocks.append(blocks.add.divider_block())
		else:
			view_blocks.append(blocks.add.simple_text_display("No results found. go back to try again"))
		return view_blocks

	@staticmethod
	def view_repair_details(meta_dict):
		view_blocks = []

		# Monday Info
		main_id = meta_dict.get('main_id') or 'new_item'

		# User Info
		user = meta_dict.get('user', {})
		username = user.get('name', 'No User Selected')
		email = user.get('email', 'No Email Provided')
		phone = user.get('phone', 'No Phone Number Provided')
		user_id = user.get('id', 'No User Selected')

		user_blocks = [
			blocks.add.section_block(
				title='*User Information*',
				accessory=blocks.elements.overflow_accessory(
					action_id=f"user_overflow__{user_id}",
					options=[
						blocks.objects.plain_text_object("Edit User Details", f"edit_user"),
						blocks.objects.plain_text_object("Change User", "change_user"),
					]
				)
			),
			blocks.add.simple_text_display(f"*Name*: {username}"),
			blocks.add.simple_text_display(f"*Email*: {email}"),
			blocks.add.simple_text_display(f"*Phone Number*: {phone}"),
			blocks.add.divider_block()
		]
		view_blocks.extend(user_blocks)

		# Repair Info
		repair_blocks = [
			blocks.add.section_block(
				title="*Repair Information*",
				accessory=blocks.elements.overflow_accessory(
					action_id=f"edit_quote__{main_id}",
					options=[blocks.objects.plain_text_object("Edit Quote", "edit_quote")]
				)
			),
		]
		total = 0
		if meta_dict.get('product_ids'):
			products = items.ProductItem.get(meta_dict['product_ids'])
			for prod in products:
				repair_blocks.append(
					blocks.add.simple_text_display(f"{prod.name}: *£{prod.price}*"),
				)
				total += int(prod.price.value)
		if meta_dict.get('custom_products'):
			custom_data = meta_dict['custom_products']
			for custom in custom_data:
				repair_blocks.append(
					blocks.add.simple_text_display(f"Custom: {custom['name']}: *£{custom['price']}*"),
				)
				total += int(custom['price'])
		if not meta_dict.get('product_ids') and not meta_dict.get('custom_products'):
			repair_blocks.append(
				blocks.add.simple_text_display(f"No products or custom lines added to this quote"),
			)

		if total:
			repair_blocks.append(blocks.add.divider_block())
			repair_blocks.append(blocks.add.header_block(f"Total: £{total}"))

		view_blocks.extend(repair_blocks)

		return view_blocks

	@staticmethod
	def show_quote_editor(meta_dict: dict):
		view_blocks = []
		total = 0

		products = items.ProductItem.get(meta_dict['product_ids'])

		view_blocks.append(blocks.add.section_block(
			title="*Standard Products*",
			accessory=blocks.elements.button_element(
				button_text="Add Products",
				button_value="add_products",
				action_id="add_products"
			)
		))

		if products:
			for product in products:
				view_blocks.append(blocks.add.section_block(
					title=f"{product.name}: *£{product.price}*",
					accessory=blocks.elements.button_element(
						button_text="Remove Product",
						button_value=str(product.id),
						action_id="remove_product",
						button_style='danger'
					)
				))
				total += int(product.price.value)
		else:
			view_blocks.append(blocks.add.simple_text_display("No products selected"))

		view_blocks.append(blocks.add.divider_block())

		view_blocks.append(blocks.add.section_block(
			title="*Custom Products*",
			accessory=blocks.elements.button_element(
				button_text="Add Custom Product",
				button_value="add_custom_product",
				action_id="add_custom_product"
			)
		))
		if meta_dict['custom_products']:
			for custom in meta_dict['custom_products']:
				view_blocks.append(blocks.add.section_block(
					title=f"{custom['name']}: *£{custom['price']}*",
					accessory=blocks.elements.button_element(
						button_text="Remove Custom Product",
						button_value=custom['id'],
						action_id="remove_custom_product",
						button_style='danger'
					)
				))
				total += int(custom['price'])
		else:
			view_blocks.append(blocks.add.simple_text_display("No custom products added"))

		view_blocks.append(blocks.add.divider_block())
		view_blocks.append(blocks.add.header_block(f"Total: £{total}"))

		return view_blocks

	@staticmethod
	def show_product_selection(meta_dict: dict):
		view_blocks = []

		device_id = meta_dict.get('device_id')
		if device_id:
			selected_device = items.DeviceItem(device_id)
			initial_device = [selected_device.name, selected_device.id]
		else:
			initial_device = None

		view_blocks.append(blocks.add.input_block(
			block_title="Select a device",
			element=blocks.elements.static_select_element(
				placeholder="Select a device",
				action_id="device_select",
				option_groups=blocks.options.generate_device_options_list()
			),
			block_id="device_select",
			dispatch_action=True,
			action_id="device_select",
			initial_option=initial_device
		))

		if device_id:
			options = blocks.options.generate_product_options(meta_dict['device_id'])

			initial_prod_options = []
			if meta_dict.get('product_ids'):
				products = items.ProductItem.get(meta_dict['product_ids'])
				for prod in products:
					initial_prod_options.append([str(prod.name), str(prod.id)])

			static_select = blocks.elements.multi_select_element(
				placeholder="Select a product",
				options=options,
				action_id="product_select"
			)

			product_block = blocks.add.input_block(
				block_title="Products",
				element=static_select,
				block_id=f"product_select__{device_id}",
				action_id='product_select',
				initial_options=initial_prod_options
			)
		else:
			product_block = blocks.add.simple_text_display("No device selected, select a device to see products")

		view_blocks.append(product_block)

		return view_blocks

	@staticmethod
	def show_custom_product_form(error_dict=None):
		view_blocks = []

		#  name element
		name_input = blocks.elements.text_input_element(
			placeholder="Enter a name for the product",
			action_id='name_input'
		)
		# price element
		price_input = blocks.elements.text_input_element(
			placeholder="Enter a price for the product",
			action_id='price_input'
		)

		# description element
		description_input = blocks.elements.text_input_element(
			placeholder="Enter a description for the product",
			action_id='description_input'
		)

		# name block
		if error_dict.get('custom_product_name'):
			hint = f":no_entry:  {error_dict['custom_product_name']}"
		else:
			hint = None

		view_blocks.append(blocks.add.input_block(
			block_title="Custom Product Name",
			element=name_input,
			block_id="custom_product_name",
			action_id="custom_product_name",
			hint=hint
		))

		# price block
		if error_dict.get('custom_product_price'):
			hint = f":no_entry:  {error_dict['custom_product_price']}"
		else:
			hint = None

		view_blocks.append(blocks.add.input_block(
			block_title="Custom Product Price",
			element=price_input,
			block_id="custom_product_price",
			action_id="custom_product_price",
			hint=hint
		))

		# description block
		if error_dict.get('custom_product_description'):
			hint = f":no_entry:  {error_dict['custom_product_description']}"
		else:
			hint = None

		view_blocks.append(blocks.add.input_block(
			block_title="Custom Product Description",
			element=description_input,
			block_id="custom_product_description",
			action_id="custom_product_description",
			hint=hint
		))

		return view_blocks


class UserInformationView:

	@staticmethod
	def user_search_view(meta_dict):
		view_blocks = []

		if meta_dict['user']['id']:
			user = None
			for att in ('name', 'email', 'phone'):
				if not meta_dict.get(att):
					if not user:
						user = zendesk_client.users(id=int(meta_dict['user']['id']))
					meta_dict[att] = getattr(user, att)

			view_blocks.append(blocks.add.section_block(
				title=f"*Selected User*",
				accessory=blocks.elements.overflow_accessory(
					action_id=f"view_user_overflow__{meta_dict['user']['id']}",
					options=[
						blocks.objects.plain_text_object("Edit User Details", f"edit_user"),
					]
				)
			))
			view_blocks.append(blocks.add.simple_text_display(str(meta_dict['user']['name'])))
			view_blocks.append(
				blocks.add.simple_context_block([str(meta_dict['user']['email']), str(meta_dict['user']['phone'])]))
		else:
			view_blocks.append(blocks.add.simple_text_display("*No user selected*"))

		view_blocks.append(blocks.add.divider_block())

		email_input_element = blocks.elements.external_select_element(
			placeholder='Enter a name or email address',
			action_id="zendesk_email_search",
			min_query_length=3,
			focus_on_load=True,
		)
		email_input_block = blocks.add.input_block(
			block_title="OR Select another user by searching name or email",
			element=email_input_element,
			block_id="zendesk_search",
			dispatch_action=True,
			action_id="zendesk_user_search"
		)
		view_blocks.append(email_input_block)

		return view_blocks


class ResultScreenViews:

	@staticmethod
	def get_loading_screen(message='Doing the thing...', modal=True):
		view_blocks = [blocks.add.header_block("Loading..."), blocks.add.simple_text_display(message)]

		if modal:
			view = blocks.base.get_modal_base("Loading...")
			view['blocks'] = view_blocks
			return view

		return view_blocks

	@staticmethod
	def get_error_screen(message='An Error Occurred', modal=True):
		view_blocks = [blocks.add.header_block("An Error Occurred"), blocks.add.simple_text_display(message)]

		if modal:
			view = blocks.base.get_modal_base("Loading...")
			view['blocks'] = view_blocks
			return view
