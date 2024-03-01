import logging
import functools
import traceback
import os

import json

from . import blocks as s_blocks, builders, helpers
from .. import monday
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
				blocks.append(s_blocks.add.simple_text_display("*MetaData*"))
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
		if not view_id:
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
			submit='Save Changes',
			callback_id='change_user'
		)
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
