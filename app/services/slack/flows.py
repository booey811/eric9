import datetime
import logging
import functools
import traceback
import os
import json

from zenpy.lib.exception import APIException
from zenpy.lib.api_objects import User, Ticket, CustomField

from . import blocks as s_blocks, builders, helpers, exceptions
from .. import monday, zendesk
from ...utilities import notify_admins_of_error
from ...errors import EricError
from ...tasks.sync_platform import sync_to_zendesk
from ...cache.rq import q_high
from ...tasks.notifications import quotes

import config

conf = config.get_config()
log = logging.getLogger('eric')


def handle_errors(func):
	@functools.wraps(func)
	def wrapper(*args, **kwargs):
		try:
			return func(*args, **kwargs)
		except Exception as e:
			# Get the FlowController instance from the arguments
			flow_controller = args[0]

			# Get the current view
			current_view = flow_controller.get_view("ERROR REPORT", submit=None, close='Close')

			# Check the environment
			if conf.CONFIG == 'development':
				# Print the current view
				str_view = json.loads(current_view)
				log.error(f"Error in view: {e}")
				log.error(json.dumps(str_view, indent=4))
			else:
				# Dump the view to an external service
				notify_admins_of_error(current_view)

			if getattr(flow_controller, 'meta', None):
				flow = flow_controller.meta.get('meta', 'unknown_flow')
				exceptions.save_metadata(flow_controller.meta, f"{flow}__{func.__name__}")

			# Reraise the exception
			raise e

	return wrapper


class FlowController:

	def __init__(self, flow, slack_client, ack, body, meta: dict = None):
		self.flow = flow
		self.client = slack_client
		self.ack = ack
		self.received_body = body
		self.blocks = []

		self.meta = {'flow': self.flow}

		if meta:
			self.meta.update(meta)

	def get_view(self, title, blocks=None, submit='Submit', close='Cancel', callback_id=None):
		view = {
			"type": "modal",
			"title": {
				"type": "plain_text",
				"text": title
			},
		}

		if not blocks:
			blocks = self.blocks or []

		if submit:
			view['submit'] = {
				"type": "plain_text",
				"text": submit
			}

		if close:
			view['close'] = {
				"type": "plain_text",
				"text": close
			}

		if callback_id:
			view['callback_id'] = callback_id

		if self.meta:
			view['private_metadata'] = json.dumps(self.meta)
			if conf.SLACK_SHOW_META == 'True' and self.flow != 'count':
				blocks.append(s_blocks.add.simple_text_display(f"*MetaData* ({len(view['private_metadata'])} chars)",
															   block_id=helpers.generate_unique_block_id()))
				blocks.append(
					s_blocks.add.simple_text_display(
						json.dumps(self.meta, indent=4)
					)
				)

		view['blocks'] = blocks
		return view

	def update_view(self, view, method='update', view_id=''):
		log.debug("Updating View")
		log.debug(view)
		if not view_id and method != 'open':
			view_id = self.received_body['view']['id']
		try:
			if method == 'update':
				return self.client.views_update(
					view_id=view_id,
					view=view
				)
			elif method == 'push':
				return self.client.views_push(
					trigger_id=self.received_body["trigger_id"],
					view=view
				)
			elif method == 'open':
				return self.client.views_open(
					trigger_id=self.received_body["trigger_id"],
					view=view
				)
			else:
				raise ValueError(f"Invalid method for slack API: {method}")
		except ValueError as e:
			raise e
		except Exception as e:
			if conf.CONFIG.lower() in ('development', 'testing'):
				from pprint import pprint as p
				p(view)
				raise e
			self.client.views_update(
				view_id=view_id,
				view=builders.ResultScreenViews.get_error_screen(f"Could Not Update View with '{method}'")
			)
			raise SlackViewUpdateError(e)


class RepairViewFlow(FlowController):

	def __init__(self, flow, slack_client, ack, body, meta: dict = None):
		super().__init__(flow=flow, slack_client=slack_client, ack=ack, body=body, meta=meta)

	def end_flow(self):
		pass

	@handle_errors
	def change_user(self, method='update', view_id=''):

		blocks = builders.UserInformationView.user_search_view(self.meta)
		view = self.get_view(
			"Change User",
			blocks=blocks,
			submit='Use details',
			callback_id='change_user'
		)
		self.update_view(view, method=method, view_id=view_id)
		self.ack()
		return True

	@handle_errors
	def edit_user(self, method='update', view_id='', errors=None):
		if errors is None:
			errors = {}
		blocks = builders.UserInformationView.edit_user_view(self.meta, errors)
		view = self.get_view(
			"Edit User",
			blocks=blocks,
			submit='Save Changes',
			callback_id='edit_user'
		)
		if method == 'ack':
			self.ack({'response_action': "update", "view": view})
			return False
		else:
			self.update_view(view, method=method, view_id=view_id)
			self.ack()
		return True

	@handle_errors
	def handle_user_details_update(self, new_user_info):
		errors = {}
		if "@" not in new_user_info['email'] or '.' not in new_user_info['email'] or ' ' in new_user_info['email']:
			errors['email'] = "Invalid Email Address"
		if new_user_info['phone'] and not new_user_info['phone'].isdigit():
			errors['phone'] = "Invalid Phone Number"

		if errors:
			view_id = self.received_body['view']['id']
			self.edit_user(method='ack', view_id=view_id, errors=errors)
			return False

		# show a loading screen while the changes occur
		loading_screen = builders.ResultScreenViews.get_loading_screen(f"Attempting User Update\n\n{new_user_info}",
																	   modal=True)

		self.ack(response_action="update", view=loading_screen)

		if new_user_info['id'] == 'new_user':
			if new_user_info['phone']:
				new_user = zendesk.client.users.create(
					User(
						name=new_user_info['name'],
						email=new_user_info['email'],
						phone=new_user_info['phone']
					)
				)
			else:
				new_user = zendesk.client.users.create(
					User(
						name=new_user_info['name'],
						email=new_user_info['email']
					)
				)
			self.meta['user']['id'] = str(new_user.id)
			self.meta['user']['name'] = str(new_user.name)
			self.meta['user']['email'] = str(new_user.email)
			self.meta['user']['phone'] = str(new_user.phone)
			self.client.views_update(
				view_id=self.received_body['view']['id'],
				view=builders.ResultScreenViews.get_success_screen(
					f"User Created Successfully. Please close this window to continue\n\n{new_user_info}")
			)
			self.change_user(method='update', view_id=self.received_body['view']['previous_view_id'])
			return True

		user = zendesk.client.users(id=int(self.meta['user']['id']))

		update_required = False
		for att in new_user_info:
			new_val = new_user_info.get(att)
			if not new_val:
				continue
			zen_val = getattr(user, att)
			if new_val != zen_val:
				update_required = True
				setattr(user, att, new_val)

		if update_required:
			try:
				user = zendesk.client.users.update(user)
				self.client.views_update(
					view_id=self.received_body['view']['id'],
					view=builders.ResultScreenViews.get_success_screen(
						f"User Updated Successfully. Please close this window to continue\n\n{new_user_info}")
				)
				self.meta['user']['name'] = user.name
				self.meta['user']['email'] = user.email
				self.meta['user']['phone'] = user.phone
				self.change_user(method='update', view_id=self.received_body['view']['previous_view_id'])
				return True
			except APIException as e:
				if 'email is already taken' in e.args[0]:
					self.client.views_update(
						view_id=self.received_body['view']['id'],
						view=builders.ResultScreenViews.get_error_screen(
							f"A user with this email already exists - try selecting that user instead\n\n{e}")
					)
					self.change_user(method='update', view_id=self.received_body['view']['previous_view_id'])
					return False
			except Exception as e:
				self.client.views_update(
					view_id=self.received_body['view']['id'],
					view=builders.ResultScreenViews.get_error_screen(
						f"An unexpected error occurred. You can try to close this view and go back if you'd like\n\n{e}")
				)
				raise e
		else:
			self.client.views_update(
				view_id=self.received_body['view']['id'],
				view=builders.ResultScreenViews.get_success_screen("No Changes Detected, hit 'Go Back' to continue")
			)
			return False

	@handle_errors
	def show_pre_check_list(self):
		loading_screen = self.client.views_push(
			trigger_id=self.received_body["trigger_id"],
			view=builders.ResultScreenViews.get_loading_screen("Fetching device", modal=True)
		)
		self.ack()

		if self.meta['pre_checks']:
			check_dicts = self.meta['pre_checks']
		else:
			# get the device, and the pre-checks attached to it
			device = monday.items.DeviceItem(self.meta['device_id']).load_from_api()
			loading_screen = self.client.views_update(
				view_id=loading_screen.data['view']['id'],
				view=builders.ResultScreenViews.get_loading_screen("Fetching Check Sets", modal=True)
			)
			pre_check_set = device.pre_check_set.load_from_api()

			loading_screen = self.client.views_update(
				view_id=loading_screen.data['view']['id'],
				view=builders.ResultScreenViews.get_loading_screen("Fetching Pre Checks", modal=True)
			)

			pre_checks = pre_check_set.get_check_items('cs_walk_pre_check')

			check_dicts = []
			for pre_check in pre_checks:
				try:
					check_meta = [_ for _ in self.meta['pre_checks'] if _['id'] == str(pre_check.id)][0]
				except IndexError:
					check_meta = {
						"id": str(pre_check.id),
						"name": str(pre_check.name),
						"answer": '',
					}
				check_dicts.append(check_meta)
				self.meta['pre_checks'] = check_dicts

		for check in check_dicts:
			pre_check_item = monday.items.misc.CheckItem(check['id']).load_from_cache()
			available_responses = pre_check_item.get_available_responses(labels=True)
			options = []
			for available_response in available_responses:
				option = {
					"text": {
						"type": "plain_text",
						"text": available_response
					},
					"value": available_response
				}
				options.append(option)

			if check['answer']:
				initial_option = [check['answer'], check['answer']]
			else:
				initial_option = None

			self.blocks.append(
				s_blocks.add.input_block(
					block_title=check['name'],
					optional=True,
					element=s_blocks.elements.radio_button_element(
						options=options,
						action_id=f"pre_check_item__{check['id']}"
					),
					initial_option=initial_option
				)
			)

		view = self.get_view(
			title="Pre-Checks",
			submit='Submit',
			close='Close',
			callback_id="pre_checks"
		)

		self.update_view(view, method='update', view_id=loading_screen.data['view']['id'])

		return view

	@handle_errors
	def show_repair_details(self, method='update', view_id='', errors=None):

		if errors is None:
			errors = []

		blocks = builders.QuoteInformationViews.view_repair_details(self.meta, errors)
		view = self.get_view(
			'View Repair',
			blocks=blocks,
			submit='Save Changes',
			close='Cancel',
			callback_id='repair_viewer'
		)

		if method == 'ack':
			self.ack({"response_action": "update", "view": view})
		else:
			self.update_view(view, method=method, view_id=view_id)
			self.ack()

		return view

	@handle_errors
	def view_quote(self, method='update', view_id=''):
		blocks = builders.QuoteInformationViews.show_quote_editor(self.meta)
		view = self.get_view(
			"Search for Repair",
			blocks=blocks,
			submit='Save Changes',
			callback_id='quote_editor'
		)
		self.update_view(view, method=method, view_id=view_id)
		self.ack()
		return True

	@handle_errors
	def add_products(self, method='update', view_id=''):
		blocks = builders.QuoteInformationViews.show_product_selection(self.meta)
		view = self.get_view(
			"Add Products",
			blocks=blocks,
			submit='Save Changes',
			callback_id='add_products'
		)
		self.update_view(view, method=method, view_id=view_id)
		self.ack()
		return True

	@handle_errors
	def add_custom_product(self, method='update', view_id='', errors=None):
		if errors is None:
			errors = {}
		device = monday.items.DeviceItem(self.meta['device_id'])
		if device:
			device_name = device.name
		else:
			device_name = None
		if not device_name:
			device_name = "Device Not Selected"
		blocks = builders.QuoteInformationViews.show_custom_product_form(errors, device_name)
		view = self.get_view(
			"Add Custom Product",
			blocks=blocks,
			submit='Save Changes',
			callback_id='add_custom_product'
		)
		if errors:
			self.ack({'response_action': "update", "view": view})
			return False
		self.update_view(view, method=method, view_id=view_id)
		self.ack()
		return True


class WalkInFlow(RepairViewFlow):

	def __init__(self, slack_client, ack, body, meta: dict = None):
		super().__init__("walk_in", slack_client, ack, body, meta)

	@handle_errors
	def todays_repairs(self):

		loading_screen = self.client.views_open(
			trigger_id=self.received_body["trigger_id"],
			view=builders.ResultScreenViews.get_loading_screen(modal=True)
		)
		self.ack()

		# Get the repairs
		results = monday.api.monday_connection.groups.get_items_by_group(monday.items.MainItem.BOARD_ID,
																		 conf.TODAYS_REPAIRS_GROUP_ID)
		results = results['data']['boards'][0]['groups'][0]['items_page']['items']
		item_data = monday.api.get_api_items([_['id'] for _ in results])
		repairs = [monday.items.MainItem(item['id'], item) for item in item_data]
		repairs = [repair for repair in repairs if 'walk' in repair.service.value.lower()]

		for repair in repairs:
			device_id = repair.device_id
			if device_id:
				device_name = monday.items.DeviceItem(device_id).name
			else:
				device_name = "Device Not Selected"

			booking_time = repair.booking_date.value
			if booking_time:
				booking_time = booking_time.strftime("%a %d %B %-I%p")
			else:
				booking_time = 'No Booking Time Provided'

			self.blocks.append(
				s_blocks.add.section_block(
					title=f"*{repair.name}*",
					accessory=s_blocks.elements.button_element(
						button_text=device_name,
						action_id=f"load_repair__{repair.id}",
						button_style="primary",
						button_value=str(repair.id)
					),
					block_id=f"repair__{repair.id}",
				)
			)
			self.blocks.append(s_blocks.add.simple_context_block([booking_time]))
			self.blocks.append(s_blocks.add.divider_block())

		view = self.get_view(
			title="Today's Repairs",
			submit='',
			close='Close'
		)

		self.update_view(view, method='update', view_id=loading_screen.data['view']['id'])

		return view

	@handle_errors
	def end_flow(self):
		exceptions.save_metadata(self.meta, f"{self.meta['flow']}__end_flow")

		try:
			user = zendesk.client.users(id=int(self.meta['user']['id']))

			if not self.meta['main_id']:
				main = monday.items.MainItem().create(user.name, reload=True)
			else:
				main = monday.items.MainItem(self.meta['main_id'])

			note = "Front of House Notes\n\nREQUESTED_PRODUCTS"
			description = ""

			device = monday.items.DeviceItem(self.meta['device_id'])
			products = monday.items.ProductItem.get(self.meta['product_ids'])

			diagnostic = False

			for prod in products:
				note += f"\n{prod.name}"
				description += f"\n{prod.name.replace(device.name, '').title()}(£{int(prod.price.value)})"
				if 'diagnostic' in prod.name.lower():
					diagnostic = True

			if not main.ticket_id.value:
				# create ticket
				subject = f"Your {device.name} Repair"
				ticket = zendesk.client.tickets.create(
					Ticket(
						requester_id=int(self.meta['user']['id']),
						description=subject,
						custom_fields=[
							CustomField(
								id=zendesk.custom_fields.FIELDS_DICT['main_item_id'],
								value=str(main.id)
							)
						],
						tags=['mondayactive']
					)
				)
				ticket = zendesk.client.tickets.create(ticket).ticket
				main.ticket_id = int(ticket.id)
			else:
				ticket = zendesk.client.tickets(id=int(main.ticket_id.value))

			main.main_status = 'Received'
			main.device_id = int(device.id)
			main.products_connect = [str(product.id) for product in products]
			main.imeisn = self.meta['imei_sn']
			main.passcode = self.meta['pc']
			main.email = user.email
			main.phone = user.phone or "No Number Found"

			try:
				deadline_dt = datetime.datetime.fromtimestamp(self.meta['deadline'])
				main.hard_deadline = deadline_dt
			except Exception as e:
				notify_admins_of_error(f"Failed to convert deadline to datetime: {e}")

			if diagnostic:
				main.repair_type = 'Diagnostic'
			else:
				main.repair_type = 'Repair'

			custom_ids = main.custom_quote_connect.value
			new_custom_ids = [str(_) for _ in self.meta['custom_products']]
			for custom_id in custom_ids:
				if str(custom_id) not in new_custom_ids:
					# delete custom line item
					try:
						monday.api.monday_connection.items.delete_item_by_id(int(custom_id))
					except Exception as e:
						notify_admins_of_error(f"Failed to delete custom line item: {e}")

			for custom in self.meta['custom_products']:
				if custom['id'] == 'new_item':
					# create custom line item
					custom_line = monday.items.misc.CustomQuoteLineItem()
					custom_line.price = int(custom['price'])
					custom_line = custom_line.create(custom['name'])
					custom_ids.append(custom_line.id)
				note += f"\n{custom['name']}"
				description += f"\n{custom['name'].title()}(£{int(custom['price'])})"
			main.custom_quote_connect = custom_ids
			main.main_status = 'Received'
			main.description = description
			main.commit()

			note += "\n\nPRE-CHECKS"
			for pre_check in self.meta['pre_checks']:
				note += f"\n*{pre_check['name']}*: {pre_check['answer']}"

			if self.meta['additional_notes']:
				note += f"\n\nADDITIONAL NOTES\n{self.meta['additional_notes']}"

			main.add_update(note, main.notes_thread_id.value)

			monday.api.monday_connection.items.change_multiple_column_values(
				main.BOARD_ID,
				main.id,
				{
					"device0": {"labels": [str(device.name)]}
				},
				create_labels_if_missing=True
			)

		except Exception as e:
			notify_admins_of_error(e)
			raise e


class HomeScreenFlow:

	def __init__(self, slack_client, body, ack):
		self.client = slack_client
		self.received_body = body
		self.ack = ack

	def show_home_screen(self):
		view = {
			"type": "home",
			"blocks": []
		}

		button_data = [
			["Walk In", "walk_from_home"],
			['Check Stock', 'check_stock'],
			['Adjust Quote', 'adjust_quote'],
			['Receive Order', 'receive_order'],
			['Start Count', 'start_count'],
			['TechChecks Test', 'checks__test'],
		]
		buttons = []
		for button in button_data:
			buttons.append(
				s_blocks.elements.button_element(
					button_text=button[0],
					button_value=button[1],
					action_id=button[1],
				)
			)

		view['blocks'].append(
			s_blocks.add.actions_block(
				block_id='home_actions',
				block_elements=buttons
			)
		)

		self.client.views_publish(
			user_id=self.received_body['event']['user'],
			view=view
		)
		return


class AdjustQuoteFlow(RepairViewFlow):

	def __init__(self, slack_client, ack, body, meta: dict = None):
		super().__init__("adjust_quote", slack_client, ack, body, meta)

	@handle_errors
	def quote_search(self):
		loading_screen = self.client.views_open(
			trigger_id=self.received_body["trigger_id"],
			view=builders.ResultScreenViews.get_loading_screen(modal=True)
		)
		blocks = builders.QuoteInformationViews.search_main_board()
		view = self.get_view(
			"Search for Quote",
			blocks=blocks,
			submit='',
			close='Cancel',
			callback_id='quote_search'
		)
		self.update_view(view, method='update', view_id=loading_screen.data['view']['id'])
		self.ack()
		return True

	@handle_errors
	def end_flow(self):

		if not self.meta['main_id']:
			raise ValueError("No Main ID Provided, should not be possible")

		main = monday.items.MainItem(self.meta['main_id'])

		main.products_connect = [str(_) for _ in self.meta['product_ids']]
		main.device_connect = [str(self.meta['device_id'])]

		custom_ids = main.custom_quote_connect.value
		new_custom_ids = [str(_) for _ in self.meta["custom_products"]]
		for custom_id in custom_ids:
			if str(custom_id) not in new_custom_ids:
				# delete custom line item
				try:
					monday.api.monday_connection.items.delete_item_by_id(int(custom_id))
				except Exception as e:
					notify_admins_of_error(f"Failed to delete custom line item: {e}")

		for custom in self.meta['custom_products']:
			if custom['id'] == 'new_item':
				# create custom line item
				custom_line = monday.items.misc.CustomQuoteLineItem()
				custom_line.price = int(custom['price'])
				custom_line = custom_line.create(custom['name'])
				custom_ids.append(custom_line.id)
		main.custom_quote_connect = custom_ids

		main.custom_quote_connect = custom_ids
		main.main_status = 'Ready to Quote'
		main.commit()
		if conf.CONFIG == 'production':
			q_high.enqueue(
				quotes.print_quote_to_zendesk,
				str(main.id)
			)
		else:
			quotes.print_quote_to_zendesk(str(main.id))

		return main


class CourierFlow(FlowController):

	def __init__(self, slack_client, ack, body, meta):
		super().__init__("courier", slack_client, ack, body, meta)


class MiscellaneousFlow(FlowController):

	def __init__(self, slack_client, ack, body, meta):
		super().__init__("miscellaneous", slack_client, ack, body, meta)

	def metadata_retrieval_menu(self):
		blocks = builders.ResultScreenViews.metadata_retrieval_view()
		view = self.get_view(
			"Metadata Retrieval Menu",
			blocks=blocks,
			close='Cancel'
		)
		self.update_view(view, method='open')
		self.ack()


class StockFlow(FlowController):

	def __init__(self, slack_client, ack, body, meta):
		super().__init__("stock", slack_client, ack, body, meta)

	@handle_errors
	def show_stock_check_menu(self):
		blocks = builders.EntityInformationViews.stock_check_entry_point()
		view = self.get_view(
			"Stock Check",
			blocks=blocks,
			close='Cancel'
		)
		self.update_view(view, method='open')
		self.ack()
		return view

	@handle_errors
	def show_stock_info(self, part_ids: list, method='update'):
		blocks = []
		for part_id in part_ids:
			part_blocks = builders.EntityInformationViews.view_part(part_id)
			blocks.extend(part_blocks)

		view = self.get_view(
			"Parts Info",
			blocks=blocks,
			submit='',
			close='Go Back'
		)

		self.update_view(view, method=method)
		self.ack()
		return view


class OrderFlow(FlowController):

	def __init__(self, slack_client, ack, body, meta=None):
		if meta is None:
			meta = {
				"order_lines": [],
				'current_line': {}
			}
		super().__init__("order", slack_client, ack, body, meta)

	@handle_errors
	def show_order_menu(self, method='update', view_id='', errors=None):
		if errors is None:
			errors = {}
		blocks = builders.OrderViews.order_build_entry_point(self.meta, errors=errors)
		view = self.get_view(
			"Build Order",
			blocks=blocks,
			close='Cancel',
			callback_id='order_build'
		)
		self.update_view(view, method=method, view_id=view_id)
		self.ack()
		return view

	@handle_errors
	def show_add_order_line_menu(self, order_line_meta, cost_method='total', method='update', view_id='', errors=None):
		if errors is None:
			errors = {}
		blocks = builders.OrderViews.add_order_line_menu(order_line_meta, cost_method=cost_method, errors=errors)
		view = self.get_view(
			"Add Order Line",
			blocks=blocks,
			close='Cancel',
			callback_id='add_order_line'
		)
		if method == 'ack':
			self.ack({'response_action': "update", "view": view})
			return False
		self.update_view(view, method=method, view_id=view_id)
		self.ack()
		return view

	@staticmethod
	def get_order_line_meta(name='', quantity=0, price=None, part_id=None):
		return {
			"name": name,
			"quantity": int(quantity),
			"price": price,
			"part_id": part_id
		}


class CountsFlow(FlowController):

	def __init__(self, slack_client, ack, body, meta=None):
		if not meta:
			meta = {
				"count_lines": [],
			}
		super().__init__("count", slack_client, ack, body, meta)

	@handle_errors
	def show_stock_count_entry_point(self):
		blocks = builders.StockCountViews.stock_count_entry_point()
		view = self.get_view(
			"Generate Stock Count",
			blocks=blocks,
			close='Cancel',
			submit="Generate",
			callback_id='stock_count_entry_point'
		)
		self.update_view(view, method='open')
		self.ack()
		return view

	@handle_errors
	def show_stock_count_form(self, device_type, part_type):

		loading_view = builders.ResultScreenViews.get_loading_screen("Fetching Devices....", modal=True)
		loading_view['external_id'] = 'loading_screen'
		f = self.ack({
			"response_action": "push",
			"view": loading_view
		})

		if device_type.lower() == 'test' and part_type.lower() == 'test':
			loading_screen = self.client.views_update(
				external_id='loading_screen',
				view=builders.ResultScreenViews.get_loading_screen("Fetching TESTS....", modal=True)
			)
			parts_data = monday.api.get_api_items(conf.MONDAY_TEST_ITEM_IDS['parts'])
		else:
			all_devices = monday.items.DeviceItem.fetch_all()
			devices = []
			part_ids = []
			for device in all_devices:
				try:
					device_type_from_monday = device.device_type.value.lower()
				except AttributeError:
					notify_admins_of_error(f"Device {device.id} has no device type: Cannot Add to Count")
					continue

				if device_type_from_monday == device_type.lower():
					devices.append(device)

			log.debug(f"Devices for count: {devices}")

			for device in devices:
				products = device.products
				for product in products:
					try:
						part_type_from_monday = product.product_type.value.lower()
					except AttributeError:
						notify_admins_of_error(f"Product {product.id} has no part type: Cannot Add to Count")
						continue

					if part_type_from_monday in part_type.lower():
						part_ids.extend(product.part_ids)

			loading_screen = self.client.views_update(
				external_id='loading_screen',
				view=builders.ResultScreenViews.get_loading_screen("Fetching Parts....", modal=True)
			)

			parts_data = monday.api.get_api_items(part_ids)

		existing_ids = set()
		all_parts = []
		for d in parts_data:
			if str(d['id']) in existing_ids:
				continue
			all_parts.append(monday.items.PartItem(d['id'], d))
			existing_ids.add(str(d['id']))
		parts_info = []
		for part in all_parts:
			parts_info.append({
				"part_id": str(part.id),
				"counted": 0,
				"expected": int(part.stock_level.value),
				"name": part.name
			})
			self.meta['count_lines'].append({
				"part_id": str(part.id),
				"counted": 0
			})

		blocks = builders.StockCountViews.stock_count_form(parts_info)
		view = self.get_view(
			"Stock Count",
			blocks=blocks,
			close='Cancel',
			callback_id='stock_count_form'
		)
		self.update_view(view, method='update', view_id=loading_screen.data['view']['id'])
		return view


class ChecksFlow(FlowController):

	def __init__(self, slack_client, ack, body, meta=None):
		if not meta:
			meta = {
				"checks": []
			}
		super().__init__("checks", slack_client, ack, body, meta)

	@handle_errors
	def show_check_form(self, main_id, checkpoint_name):

		self.meta['main_id'] = main_id
		self.meta['checkpoint_name'] = checkpoint_name

		main_item = monday.items.MainItem(main_id).load_from_api()
		device_id = main_item.device_id

		blocks = builders.CheckViews.show_check_form(device_id, checkpoint_name)
		view = self.get_view(
			"Checks",
			blocks=blocks,
			close='Cancel',
			callback_id='checks_form'
		)
		self.update_view(view, method='update', view_id=self.received_body['view']['id'])
		self.ack()
		return view

	@staticmethod
	def process_submission_data(main_id, submission_values, checkpoint_name="Test"):

		# get the results item, if None, create it
		try:
			results = monday.api.monday_connection.items.fetch_items_by_column_value(
				monday.items.misc.CheckResultItem.BOARD_ID,
				"text__1",
				str(main_id)
			)
		except Exception as e:
			raise monday.api.exceptions.MondayAPIError(f"Failed to fetch results item: {e}")

		results_item_data = results.get('data', {}).get('items_page_by_column_values', {}).get('items', [])

		if results_item_data:
			results_item = monday.items.misc.CheckResultItem(results_item_data[0]['id'],
															 results_item_data[0]).load_from_api()
		else:
			name = f"Check Results for {main_id}"
			results_item = monday.items.misc.CheckResultItem()
			results_item.main_item_id = str(main_id)
			results_item = results_item.create(name)

		results_item.slack_answer_values = json.dumps(submission_values)
		results_item.commit()

		check_ids = [_ for _ in submission_values]
		check_item_data = monday.api.get_api_items(check_ids)
		check_items = [monday.items.misc.CheckItem(_['id'], _) for _ in check_item_data]
		results_col_data = {
			"text55__1": checkpoint_name,
		}

		for check_id in submission_values:
			answer_data = submission_values[check_id]["check_action__" + check_id]
			if answer_data.get('type') in ('radio_buttons', 'static_select'):
				answer = answer_data['selected_option']['value']
			elif answer_data.get('type') == 'multi_static_select':
				answer = ", ".join([_['value'] for _ in answer_data['selected_options']])
			elif answer_data.get('type') in ('plain_text_input', 'number_input'):
				answer = answer_data['value']
			else:
				answer = None

			check_item = [_ for _ in check_items if str(_.id) == str(check_id)][0]
			col_data = check_item.get_result_column_data(answer)
			results_col_data.update(col_data)

		create_subitem = monday.api.monday_connection.items.create_subitem(
			parent_item_id=int(results_item.id),
			subitem_name="Check Results",
			column_values=results_col_data
		)
		monday.api.monday_connection.updates.create_update(
			item_id=create_subitem['data']['create_subitem']['id'],
			update_value=json.dumps(submission_values, indent=4)
		)

		return results_item.id


def get_flow(flow_name, slack_client, ack, body, meta=None):
	if flow_name == 'walk_in':
		return WalkInFlow(slack_client, ack, body, meta)
	elif flow_name == 'adjust_quote':
		return AdjustQuoteFlow(slack_client, ack, body, meta)
	elif flow_name == 'courier':
		return CourierFlow(slack_client, ack, body, meta)
	else:
		raise ValueError(f"Invalid Flow: {flow_name}")


class SlackViewUpdateError(EricError):
	pass
