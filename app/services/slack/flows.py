import logging
import functools
import traceback
import os
import json

from zenpy.lib.exception import APIException
from zenpy.lib.api_objects import User

from . import blocks as s_blocks, builders, helpers, exceptions
from .. import monday, zendesk
from ...utilities import notify_admins_of_error
from ...errors import EricError

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
			if conf.SLACK_SHOW_META:
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

	def show_pre_check_list(self):
		loading_screen = self.client.views_push(
			trigger_id=self.received_body["trigger_id"],
			view=builders.ResultScreenViews.get_loading_screen("Fetching device", modal=True)
		)
		self.ack()

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

		pre_checks = pre_check_set.get_pre_check_items()

		check_dicts = []
		for pre_check in pre_checks:
			try:
				check_meta = [_ for _ in self.meta['pre_checks'] if _['id'] == str(pre_check.id)][0]
			except IndexError:
				check_meta = {
					"id": str(pre_check.id),
					"name": str(pre_check.name),
					"answer": '',
					"available_answers": pre_check.get_available_responses()
				}
			check_dicts.append(check_meta)

			# add one block per pre check item, then the available responses are options`

			# Split checks into sets of 10 and add them to blocks
			num_sets = len(check_dicts) // 10
			for i in range(num_sets):
				start_index = i * 10
				end_index = start_index + 10
				checks_set = check_dicts[start_index:end_index]

				options = []
				for check in checks_set:
					option = {
						"text": {
							"type": "plain_text",
							"text": check['name']
						},
						"value": str(check['id'])
					}
					options.append(option)

				self.blocks.append(
					s_blocks.add.input_block(
						block_title='Pre-Checks',
						element=s_blocks.elements.checkbox_element(
							options=options,
							action_id=f"pre_check_set_{i + 1}"
						)
					)
				)

		view = self.get_view(
			title="Today's Repairs",
			submit='Submit',
			close='Close'
		)

		self.update_view(view, method='update', view_id=loading_screen.data['view']['id'])

		return view


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
	def show_repair_details(self, method='update', view_id=''):

		blocks = builders.QuoteInformationViews.view_repair_details(self.meta)
		view = self.get_view(
			'View Repair',
			blocks=blocks,
			submit='Save Changes',
			close='Cancel',
			callback_id='repair_viewer'
		)

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
		blocks = builders.QuoteInformationViews.show_custom_product_form(errors)
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


class AdjustQuoteFlow(FlowController):

	def __init__(self, slack_client, ack, body, meta: dict = None):
		super().__init__("adjust_quote", slack_client, ack, body, meta)


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
