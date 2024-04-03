import datetime
from typing import List
import json

from . import blocks, exceptions
from .. import monday
from ..monday import items
from ..zendesk import helpers as zendesk_helpers, client as zendesk_client
from ...cache import get_redis_connection
import config

conf = config.get_config()


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
		part = items.PartItem(part_id).load_from_api()
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

	@staticmethod
	def stock_check_entry_point():
		results = []

		# use an external select menu to search for a part
		results.append(
			blocks.add.input_block(
				block_title="Search for a part",
				element=blocks.elements.external_select_element(
					placeholder='Enter a part name',
					action_id="stock_check_part",
					min_query_length=3,
					focus_on_load=True,
				),
				block_id="part_search",
				dispatch_action=True,
				action_id="stock_check_part"
			)
		)

		return results


class OrderViews:

	@staticmethod
	def order_build_entry_point(meta_dict, errors=None):
		if errors is None:
			errors = {}
		view_blocks = []
		# use an external select menu to search for a part
		view_blocks.append(
			blocks.add.input_block(
				block_title="Search for a part",
				element=blocks.elements.external_select_element(
					placeholder='Enter a part name',
					action_id="order_part_search",
					min_query_length=3,
					focus_on_load=True,
				),
				block_id="part_search",
				dispatch_action=True,
				action_id="order_part_search"
			)
		)

		if errors.get("part_id"):
			view_blocks.append(blocks.add.simple_text_display(f":no_entry:  *{errors['part_id']}*"))

		order_line_blocks = []
		order_total = 0
		if meta_dict.get('order_lines'):
			for line in meta_dict['order_lines']:
				line_total = round(float(line['price']) * int(line['quantity']), 3)
				order_total += line_total
				order_line_block = [
					blocks.add.section_block(
						title=f"*{line['name']}: {line['quantity']}*",
						accessory=blocks.elements.button_element(
							button_text="Remove",
							button_value=line['part_id'],
							action_id=f"remove_order_line__{line['part_id']}",
							button_style='danger'
						)
					),
					blocks.add.simple_context_block([f"Total Cost: £{line_total}"])
				]
				order_line_blocks.extend(order_line_block)
			order_line_blocks.append(blocks.add.divider_block())
			order_line_blocks.append(blocks.add.header_block(f"Total: £{order_total}"))
		view_blocks.extend(order_line_blocks)

		return view_blocks

	@staticmethod
	def add_order_line_menu(order_line_meta, cost_method='total', errors=None):
		if errors is None:
			errors = {}
		if order_line_meta is None:
			order_line_meta = {}

		if order_line_meta:
			quantity = order_line_meta['quantity']
			price = order_line_meta['price']
		else:
			quantity = None
			price = None

		if errors.get('quantity_input'):
			quant_hint = f":no_entry:  {errors['quantity_input']}"
		else:
			quant_hint = None

		view_blocks = [
			blocks.add.header_block(f"Add {order_line_meta['name'][:145]}"),
			blocks.add.input_block(
				block_title="Quantity",
				block_id='quantity_input',
				element=blocks.elements.text_input_element(
					placeholder="Enter a quantity",
					action_id="quantity_input",
					initial_value=quantity
				),
				hint=quant_hint
			),
		]

		costing_options = [
			blocks.objects.plain_text_object(_[0], _[1]) for _ in [
				["Total Cost", "total"],
				["Cost Per Unit", "unit"]
			]
		]

		if cost_method == 'unit':
			price_hint = 'Enter the price per single item in the order line'
			initial_costing = ["Cost Per Unit", "unit"]
		else:
			price_hint = 'Enter the total cost for all items in the order line'
			initial_costing = ["Total Cost", "total"]

		view_blocks.append(
			blocks.add.input_block(
				block_title="Costing Method",
				block_id='costing_method',
				element=blocks.elements.radio_button_element(
					action_id="costing_method",
					options=costing_options,
				),
				action_id="costing_method",
				dispatch_action=True,
				initial_option=initial_costing
			)
		)

		if errors.get('price_input'):
			price_hint = f":no_entry:  {errors['price_input']}"

		price_block = blocks.add.input_block(
			block_title="Price",
			block_id='price_input',
			element=blocks.elements.text_input_element(
				placeholder=price_hint,
				action_id="price_input",
				initial_value=price
			),
			hint=price_hint
		)

		view_blocks.append(price_block)

		return view_blocks


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

		view_blocks.append(blocks.add.divider_block())
		view_blocks.append(blocks.add.simple_text_display("*OR* Browse Diagnostic Complete Items"))

		search = monday.items.MainItem(search=True)
		raw_results = monday.api.monday_connection.items.fetch_items_by_column_value(search.BOARD_ID, 'status4',
																					 'Diagnostic Complete')
		result_item_data = raw_results['data']['items_page_by_column_values']['items']
		results = [monday.items.MainItem(result['id'], result) for result in result_item_data]

		for m in results:
			if m.device_id:
				device = items.DeviceItem(m.device_id)
			else:
				device = items.DeviceItem(4028854241)
			view_blocks.append(
				blocks.add.section_block(
					title=f"*{m.name}*",
					accessory=blocks.elements.button_element(
						button_text=device.name,
						action_id=f"load_repair__{m.id}",
						button_style="primary",
						button_value=str(m.id)
					),
					block_id=f"repair__{m.id}",
				)
			)
			view_blocks.append(blocks.add.divider_block())

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
	def view_repair_details(meta_dict, errors=None):
		if errors is None:
			errors = []
		view_blocks = []

		# Monday Info
		main_id = meta_dict.get('main_id') or 'new_item'

		# add errors, if any
		if errors:
			for error in errors:
				view_blocks.append(blocks.add.simple_text_display(f":no_entry:  *{error}*"))
			view_blocks.append(blocks.add.divider_block())

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
		diagnostic = False
		max_turnaround = 0
		if meta_dict.get('product_ids'):
			products = items.ProductItem.get(meta_dict['product_ids'])
			for prod in products:
				repair_blocks.append(
					blocks.add.simple_text_display(f"{prod.name}: *£{prod.price}*"),
				)
				total += int(prod.price.value)
				if 'diagnostic' in prod.name.lower():
					diagnostic = True
				if prod.turnaround.value:
					if int(prod.turnaround.value) > int(max_turnaround):
						max_turnaround = prod.turnaround.value
		if meta_dict.get('custom_products'):
			custom_data = meta_dict['custom_products']
			for custom in custom_data:
				repair_blocks.append(
					blocks.add.simple_text_display(f"Custom: {custom['name']}: *£{custom['price']}*"),
				)
				total += int(custom['price'])

		if meta_dict.get('deadline'):
			deadline = meta_dict['deadline']
		else:
			if max_turnaround:
				now = datetime.datetime.now()
				deadline = now + datetime.timedelta(hours=int(max_turnaround))
				deadline = int(deadline.timestamp())
			else:
				deadline = None

		repair_blocks.append(
			blocks.add.input_block(
				block_title="Deadline",
				block_id='deadline',
				element=blocks.elements.datetime_picker_element(
					initial_dt=deadline,
					action_id='deadline',
				),
				optional=False
			)
		)

		if not meta_dict.get('product_ids') and not meta_dict.get('custom_products'):
			repair_blocks.append(
				blocks.add.simple_text_display(f"No products or custom lines added to this quote"),
			)

		if total:
			repair_blocks.append(blocks.add.header_block(f"Total: £{total}"))

		if meta_dict['pay_status'] == 'Confirmed':
			repair_blocks.append(blocks.add.simple_text_display(":white_check_mark:  Payment has already been taken"))

		view_blocks.extend(repair_blocks)

		# pre check info
		pre_check_blocks = [
			blocks.add.divider_block(),
			blocks.add.header_block("Pre-Checks & Information"),
		]
		if not meta_dict.get('device_id'):
			pre_check_blocks.append(
				blocks.add.simple_text_display("No device selected, select a device to see pre-checks"))
		else:
			if meta_dict.get('pre_checks'):
				completed = True
				for pre_check in meta_dict['pre_checks']:
					if not pre_check.get('answer'):
						completed = False
						break
				if completed:
					pre_check_blocks.append(
						blocks.add.actions_block(
							block_elements=[
								blocks.elements.button_element(":white_check_mark:  Checks Complete", "open_pre_checks",
															   f"open_pre_checks__{meta_dict['device_id']}")])
					)
				else:
					# add a button to open pre-check view (which will fetch the pre_checks and add them to meta)
					pre_check_blocks.append(
						blocks.add.actions_block(
							block_elements=[
								blocks.elements.button_element(":no_entry:  Checks Not Completed", "open_pre_checks",
															   f"open_pre_checks__{meta_dict['device_id']}")])
					)
			else:
				# add a button to open pre-check view (which will fetch the pre_checks and add them to meta)
				pre_check_blocks.append(
					blocks.add.actions_block(
						block_elements=[
							blocks.elements.button_element(":no_entry:  Checks Not Completed", "open_pre_checks",
														   f"open_pre_checks__{meta_dict['device_id']}")])
				)

		view_blocks.extend(pre_check_blocks)

		notes_blocks = []
		if meta_dict.get('additional_notes'):
			initial_notes = meta_dict['additional_notes']
		else:
			initial_notes = None

		if diagnostic:
			notes_optional = False
		else:
			notes_optional = True

		notes_blocks.append(
			blocks.add.input_block(
				block_title="Additional Notes",
				block_id='additional_notes',
				element=blocks.elements.text_input_element(
					placeholder="Enter additional notes for this repair",
					action_id="additional_notes",
					multiline=True,
					initial_value=initial_notes,
					dispatch_config=True
				),
				optional=notes_optional,
				dispatch_action=True,
				action_id='additional_notes'
			)
		)

		if meta_dict.get('imei_sn'):
			initial_imei = meta_dict['imei_sn']
		else:
			initial_imei = None

		if meta_dict.get('pc'):
			initial_passcode = meta_dict['pc']
		else:
			initial_passcode = None

		notes_blocks.append(
			blocks.add.input_block(
				block_title="IMEI/SN",
				element=blocks.elements.text_input_element(
					placeholder="Enter a note",
					initial_value=initial_imei,
					action_id='imei_sn',
					dispatch_config=True
				),
				block_id="imei_sn",
				optional=False,
				action_id='imei_sn',
				dispatch_action=True,
			)
		)

		notes_blocks.append(
			blocks.add.input_block(
				block_title="Password",
				element=blocks.elements.text_input_element(
					placeholder="Enter a passcode",
					initial_value=initial_passcode,
					action_id='pc',
					dispatch_config=True
				),
				block_id="pc",
				optional=False,
				action_id='pc',
				dispatch_action=True,
			)
		)

		view_blocks.extend(notes_blocks)

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
					if str(prod.device_id) == str(device_id):
						initial_prod_options.append([str(prod.name), str(prod.id)])
					else:
						meta_dict['product_ids'].remove(prod.id)

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

	@staticmethod
	def show_pre_check_view(pre_checks: List[items.misc.PreCheckItem]):
		view_blocks = []

		for check in pre_checks:
			view_blocks.append(blocks.add.section_block(
				title=check.name,
				accessory=blocks.elements.button_element(
					button_text="View",
					button_value=str(check.id),
					action_id="view_pre_check"
				)
			))
		return view_blocks


class StockCountViews:

	@staticmethod
	def stock_count_entry_point():
		"""show options for generating the subsequent count forms"""
		view_blocks = []

		device_types = ['iPhone', 'iPad', 'Mac', 'Watch', 'MacBook', 'Other']
		if conf.CONFIG == 'TESTING':
			device_types.append('Test')

		view_blocks.append(
			blocks.add.input_block(
				block_title="Select a device type",
				element=blocks.elements.static_select_element(
					placeholder="Select a device type",
					action_id="stock_count_device_type",
					options=[blocks.objects.option_object(_, _.lower()) for _ in device_types]
				),
				block_id="device_type_select",
				action_id="stock_count_device_type"
			)
		)

		part_types = ['Screen/LCD', 'Battery', 'Rear Camera', 'Other']
		if conf.CONFIG == 'TESTING':
			part_types.append('Test')

		view_blocks.append(
			blocks.add.input_block(
				block_title="Select a part type",
				element=blocks.elements.static_select_element(
					placeholder="Select a part type",
					action_id="stock_count_part_type",
					options=[blocks.objects.option_object(_, _.lower()) for _ in part_types]
				),
				block_id="part_type_select",
				action_id="stock_count_part_type"
			)
		)

		return view_blocks

	@staticmethod
	def stock_count_form(count_lines):
		view_blocks = []

		count_lines = sorted(count_lines, key=lambda x: x['name'])

		for line in count_lines:
			if line['counted']:
				initial = line['counted']
			else:
				initial = None
			view_blocks.append(blocks.add.input_block(
				block_title=f"{line['name']} ({line['expected']})",
				element=blocks.elements.text_input_element(
					placeholder=0,
					action_id=f"stock_count__{line['part_id']}",
					initial_value=initial
				),
				block_id=f"stock_count__{line['part_id']}",
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

	@staticmethod
	def edit_user_view(meta_dict, errors=None):
		if errors is None:
			errors = {}
		view_blocks = []

		user_dict = meta_dict.get('user', {})
		for att in ('name', 'email', 'phone'):
			if att in ('name', 'email'):
				optional = False
			else:
				optional = True

			if errors.get(att):
				hint = f":no_entry:  {errors[att]}"
			else:
				hint = None

			view_blocks.append(blocks.add.input_block(
				block_title=att.capitalize(),
				element=blocks.elements.text_input_element(
					placeholder=f"Enter a new {att} for the user",
					initial_value=user_dict.get(att, None),
					action_id=f"edit_user__{att}"
				),
				block_id='edit_user__' + att,
				optional=optional,
				hint=hint
			)
			)
		#
		# if meta_dict['user']['id']:
		# 	user = zendesk_client.users(id=int(meta_dict['user']['id']))
		# 	view_blocks.append(blocks.add.section_block(
		# 		title=f"*{user.name}*",
		# 		accessory=blocks.elements.overflow_accessory(
		# 			action_id=f"view_user_overflow__{meta_dict['user']['id']}",
		# 			options=[
		# 				blocks.objects.plain_text_object("View User Details", f"view_user"),
		# 			]
		# 		)
		# 	))
		# 	view_blocks.append(blocks.add.simple_text_display(str(user.email)))
		# 	view_blocks.append(blocks.add.simple_text_display(str(user.phone)))
		# else:
		# 	view_blocks.append(blocks.add.simple_text_display("*No user selected*"))
		#
		# view_blocks.append(blocks.add.divider_block())
		#
		# email_input_element = blocks.elements.external_select_element(
		# 	placeholder='Enter a name or email address',
		# 	action_id="zendesk_email_search",
		# 	min_query_length=3,
		# 	focus_on_load=True,
		# )
		# email_input_block = blocks.add.input_block(
		# 	block_title="Select another user by searching name or email",
		# 	element=email_input_element,
		# 	block_id="zendesk_search",
		# 	dispatch_action=True,
		# 	action_id="zendesk_user_search"
		# )
		# view_blocks.append(email_input_block)

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
			view = blocks.base.get_modal_base("Loading...", cancel='Go Back', submit=False)
			view['blocks'] = view_blocks
			return view

	@staticmethod
	def get_success_screen(message='Success!', modal=True):
		view_blocks = [blocks.add.header_block("Success!"), blocks.add.simple_text_display(message)]

		if modal:
			view = blocks.base.get_modal_base("Loading...", submit=False, cancel='Continue')
			view['blocks'] = view_blocks
			return view

	@staticmethod
	def metadata_retrieval_view():
		view_blocks = []

		metadata_sets = get_redis_connection().keys("slack_meta:*")

		for meta_set in metadata_sets:
			data_set = get_redis_connection().get(meta_set)
			if not data_set:
				continue

			meta = data_set.decode('utf-8')
			try:
				meta = json.loads(meta)
			except json.JSONDecodeError:
				continue

			flow = meta.get('flow', 'Unknown Workflow')

			user_dict = meta.get('user', {})
			user_name = user_dict.get('name', 'No Name Provided')

			device_id = meta.get('device_id')
			if device_id:
				device = items.DeviceItem(device_id)
				device_name = device.name
			else:
				device_name = "No Device Selected"

			view_blocks.append(
				blocks.add.section_block(
					title=f"{flow}: {user_name}",
					accessory=blocks.elements.button_element(
						button_text="View",
						button_value=meta_set.decode('utf-8'),
						action_id=f"revive_metadata"
					)
				)
			)
			view_blocks.append(blocks.add.simple_context_block([f"Device: {device_name}"]))
		return view_blocks
