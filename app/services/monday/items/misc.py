import time
import json

from zenpy.lib.api_objects import Ticket, CustomField, Comment

from ..api.items import BaseItemType, BaseCacheableItem
from ..api import columns, get_api_items, exceptions, monday_connection, get_items_by_board_id
from ..api.exceptions import MondayDataError
from ... import typeform
from ..items import MainItem
from ...zendesk import helpers, client as zendesk_client, custom_fields
from ...slack import blocks
from ....utilities import notify_admins_of_error


class WebBookingItem(BaseItemType):
	BOARD_ID = 973467694

	def __init__(self, item_id=None, api_data: dict | None = None, search: bool = False):
		self.transfer_status = columns.StatusValue("status_18")

		self.woo_commerce_order_id = columns.TextValue('order_id')

		self.pay_status = columns.StatusValue("payment_status")
		self.pay_method = columns.StatusValue("payment_method")

		self.booking_notes = columns.TextValue('notes')
		self.secondary_notes = columns.LongTextValue('enquiry')

		self.phone = columns.TextValue('phone_number')
		self.email = columns.TextValue('email')

		self.service = columns.StatusValue('service')
		self.client = columns.StatusValue('client')
		self.repair_type = columns.StatusValue('type')

		self.booking_date = columns.DateValue('booking_time')

		self.address_postcode = columns.TextValue('post_code')
		self.address_notes = columns.TextValue('company_flat')
		self.address_street = columns.TextValue('street_name_number')
		self.point_of_collection = columns.TextValue('text9')

		self.main_item_id = columns.TextValue("text1")

		self.device_text = columns.TextValue("text__1")
		self.repairs_text = columns.TextValue("text1__1")

		super().__init__(item_id=item_id, api_data=api_data, search=search)


class WebEnquiryItem(BaseItemType):
	BOARD_ID = 863729294

	def __init__(self, item_id=None, api_data: dict | None = None, search: bool = False):
		self.phone = columns.TextValue('text0')
		self.email = columns.TextValue('text')

		self.zendesk_id = columns.TextValue("zendesk_id")

		self.device_type_string = columns.TextValue('text06')
		self.model_string = columns.TextValue('text2')

		self.body = columns.TextValue("long_text")

		self.fault_type = columns.StatusValue("status6")

		self.converted_status = columns.StatusValue("converted")
		self.date_received = columns.DateValue("date9")

		super().__init__(item_id=item_id, api_data=api_data, search=search)


class TypeFormWalkInResponseItem(BaseItemType):
	BOARD_ID = 4752037048

	FORM_ID = "LtNyVqVN"

	def __init__(self, item_id=None, api_data: dict | None = None, search: bool = False):
		self.form_type = columns.StatusValue('status4')
		self.phone = columns.TextValue('text')
		self.email = columns.TextValue('text_1')
		self.device_type = columns.StatusValue('device_category')
		self.device = columns.TextValue('device6')
		self.repair_notes = columns.TextValue('text7')
		self.push_to_slack = columns.StatusValue('status6')

		super().__init__(item_id=item_id, api_data=api_data, search=search)

	def sync_typeform_data(self):

		def get_answer_by_field_id(f_id):
			return [ans for ans in most_recent['answers'] if ans['field']['ref'] == f_id][0]

		typeform_field_refs = {
			'form_type': 'fc093e51-6c78-470d-a6be-f907db22ffcc',
			'phone': '399e680c-f83f-4fd6-bd86-1cb9a0d09512',
			'email': 'ad62f045-c8a6-4fb2-8442-f5c6d0a4abe1',
			'device_type': 'c6c7c1d0-e016-480e-ac37-d25a312d5cd6',
			'device': [
				"26897f28-6841-4843-9b8f-be9843c01619",
				"f8e0ff65-d7f7-4eb9-b577-7f97e71ffb69",
				"45659e19-2e03-49d2-b436-e7de14323fd2",
				"e8ed9ec8-19df-4931-a416-a1e9b3d26073",
				"e3182fa4-e140-498a-b6f1-a01a1511e18a"
			],
			'repair_notes': '7671671d-827d-4b36-882d-e5600b02cee5'
		}

		# Get the most recent response from the form
		typeform_data_items = typeform.client.get_responses(
			form_id=self.FORM_ID,
			query=self.email
		)

		most_recent = typeform_data_items['items'][0]

		# Update the item with the most recent data
		self.phone = get_answer_by_field_id(typeform_field_refs['phone'])['text']
		self.email = get_answer_by_field_id(typeform_field_refs['email'])['email']
		self.device_type = get_answer_by_field_id(typeform_field_refs['device_type'])['choice']['label']
		self.repair_notes = get_answer_by_field_id(typeform_field_refs['repair_notes'])['text']
		self.form_type = get_answer_by_field_id(typeform_field_refs['form_type'])['choice']['label']

		for field_id in typeform_field_refs['device']:
			try:
				device_answer_dict = get_answer_by_field_id(field_id)
				self.device = device_answer_dict['text']
				break
			except IndexError:
				continue

		zendesk_user_results = helpers.search_zendesk(self.email.value)
		if not zendesk_user_results:
			user = helpers.create_user(
				name=self.name,
				email=self.email.value,
				phone=self.phone.value
			)
		else:
			user = next(zendesk_user_results)

		main = MainItem()
		main.create(name=self.name, reload=True)

		subject = f"Your {self.device_type.value} Repair with iCorrect"

		ticket = Ticket(
			requester_id=user.id,
			description=subject,
			custom_fields=[
				CustomField(id=custom_fields.FIELDS_DICT['main_item_id'], value=str(main.id))
			],
			comment=Comment(
				public=False,
				body=subject
			)
		)

		ticket = zendesk_client.tickets.create(ticket).ticket

		main.ticket_id = str(ticket.id)
		main.description = str(self.repair_notes)
		main.client = 'End User'
		main.service = 'Walk-In'
		main.ticket_url = [str(ticket.id), f"https://icorrect.zendesk.com/agent/tickets/{ticket.id}"]
		main.commit()

		self.push_to_slack = 'Do Now!'
		self.commit()

		return self


class NotificationMappingItem(BaseItemType):
	BOARD_ID = 3428830196

	def __init__(self, item_id=None, api_data: dict | None = None, search: bool = False):
		self.macro_search_term = columns.TextValue('text8')
		self.macro_id = columns.TextValue("text")

		super().__init__(item_id=item_id, api_data=api_data, search=search)


class RepairSessionItem(BaseItemType):
	BOARD_ID = 5997573759

	def __init__(self, item_id=None, api_data: dict | None = None, search: bool = False):
		self.main_board_id = columns.TextValue('text')
		self.start_time = columns.DateValue("date")
		self.end_time = columns.DateValue("date2")
		self.session_status = columns.StatusValue("status0")
		self.device_id = columns.TextValue("text8")

		self.phase_label = columns.TextValue("text7")
		self.ending_status = columns.TextValue("text5")

		self.technician = columns.PeopleValue("people")

		self.gcal_event_id = columns.TextValue("text0")
		self.gcal_plot_status = columns.StatusValue("status3")

		super().__init__(item_id=item_id, api_data=api_data, search=search)

	def get_session_duration(self):
		# calculate the duration of the session in minutes from self.start_time and self.end_time
		start_time = self.start_time.value
		end_time = self.end_time.value
		duration = end_time - start_time
		return duration.total_seconds() / 60


class CustomQuoteLineItem(BaseItemType):
	BOARD_ID = 4570780706

	def __init__(self, item_id=None, api_data: dict | None = None, search: bool = False):
		self.description = columns.TextValue('repair_description')
		self.price = columns.NumberValue('numbers')
		self.turnaround = columns.NumberValue('numbers3')

		super().__init__(item_id=item_id, api_data=api_data, search=search)

	def prepare_cache_data(self):
		return {
			"id": str(self.id),
			"description": self.description.value,
			"price": self.price.value,
			"name": self.name
		}


class RepairProfitModelItem(BaseItemType):
	BOARD_ID = 5938137198

	def __init__(self, item_id=None, api_data: dict | None = None, search: bool = False):
		self.products_connect = columns.ConnectBoards("connect_boards")
		self.parts_connect = columns.ConnectBoards("connect_boards4")

		super().__init__(item_id=item_id, api_data=api_data, search=search)


class PreCheckSet(BaseCacheableItem):
	BOARD_ID = 4347106321

	AVAILABLE_CHECKPOINTS = [
		["cs_walk_pre_check", 'cs_walk_pre_check_connect'],  # walk-ins
		["tech_post_check", "tech_post_check_connect"]  # technicians following a repair
	]

	def __init__(self, item_id=None, api_data: dict | None = None, search: bool = False):
		self.set_type = columns.StatusValue('status9')
		self.cs_walk_pre_check_connect = columns.ConnectBoards('connect_boards4')
		self.tech_post_check_connect = columns.ConnectBoards("connect_boards__1")

		self._pre_check_items = None

		super().__init__(item_id=item_id, api_data=api_data, search=search)

	def cache_key(self):
		return "pre_check_set:" + str(self.id)

	def prepare_cache_data(self):
		return {
			"name": str(self.name),
			"id": str(self.id),
			"set_type": self.set_type.value,
			"cs_walk_pre_check_ids": self.cs_walk_pre_check_connect.value
		}

	def load_from_cache(self, cache_data=None):
		if cache_data is None:
			cache_data = self.fetch_cache_data()
		self.set_type.value = cache_data['set_type']
		self.cs_walk_pre_check_connect.value = cache_data['cs_walk_pre_check_ids']
		self.id = cache_data['id']
		self.name = cache_data['name']
		return self

	def get_check_items(self, checkpoint_name):
		# select the correct attribute for the check set requested

		for checkpoint in self.AVAILABLE_CHECKPOINTS:
			if checkpoint_name == checkpoint[0]:
				connect_col = getattr(self, checkpoint[1])
				break
		else:  # This else clause corresponds to the for loop, not the if statement
			raise ValueError(f"No Checkpoint Available For: {checkpoint_name}")

		check_item_ids = connect_col.value
		check_items = [CheckItem(i['id'], i) for i in get_api_items(check_item_ids)]
		return check_items


class CheckItem(BaseCacheableItem):
	BOARD_ID = 4455646189

	@classmethod
	def get_all(cls):
		item_data = get_items_by_board_id(cls.BOARD_ID)
		return [cls(i['id'], i) for i in item_data]

	def __init__(self, item_id=None, api_data: dict | None = None, search: bool = False):
		self.available_responses = columns.DropdownValue('dropdown')
		self.positive_responses = columns.DropdownValue('dropdown6__1')
		self.check_category = columns.StatusValue('status0__1')
		self.requires_power = columns.CheckBoxValue('checkbox')

		self.conditional = columns.CheckBoxValue("checkbox__1")
		self.conditional_tag = columns.TextValue("text0__1")

		self.check_sets_connect = columns.ConnectBoards('board_relation')

		self.results_column_id = columns.TextValue("text__1")

		self.response_type = columns.StatusValue("status__1")

		super().__init__(item_id=item_id, api_data=api_data, search=search)

	def cache_key(self):
		return "pre_check_item:" + str(self.id)

	def prepare_cache_data(self):
		return {
			"name": str(self.name),
			"id": str(self.id),
			"available_responses": self.available_responses.value,
			"check_set_ids": self.check_sets_connect.value
		}

	def load_from_cache(self, cache_data=None):
		if cache_data is None:
			cache_data = self.fetch_cache_data()
		self.available_responses.value = cache_data['available_responses']
		self.check_sets_connect.value = cache_data['check_set_ids']
		self.id = cache_data['id']
		self.name = cache_data['name']
		return self

	@property
	def check_sets(self):
		if not self.check_sets_connect.value:
			return []
		item_data = get_api_items(self.check_sets_connect.value)
		return [PreCheckSet(i['id'], i) for i in item_data]

	def get_available_responses(self, labels=True):
		result_ids = self.available_responses.value
		if not result_ids:
			self.load_from_api()
			result_ids = self.available_responses.value
			if not result_ids:
				raise CheckDataError(f"{self} could not load available responses: {self._api_data}")
		if labels:
			labels = self.convert_dropdown_ids_to_labels(result_ids, self.available_responses.column_id)
			return labels
		else:
			return result_ids

	def get_slack_block(self):

		action_id = f"check_action__{self.id}"

		# return a slack block with the check item's name and available responses
		if self.response_type.value == 'Text Input':
			element = blocks.elements.text_input_element(
				action_id=action_id,
				placeholder="",
			)
		elif self.response_type.value == 'Number Input':
			element = blocks.elements.number_input_element(
				action_id=action_id,
				decimal_allowed=True,
			)
		elif self.response_type.value == 'Single Select':
			options = [blocks.objects.option_object(x, x) for x in self.get_available_responses()]
			element = blocks.elements.static_select_element(
				action_id=action_id,
				options=options,
				placeholder=self.name,
			)
		elif self.response_type.value == "Multi-Select":
			options = [blocks.objects.option_object(x, x) for x in self.get_available_responses()]
			element = blocks.elements.multi_select_element(
				action_id=action_id,
				options=options,
				placeholder=self.name
			)
		else:
			raise MondayDataError(f"{self} has Unknown response type: {self.response_type.value}")

		if self.conditional.value:
			if not self.conditional_tag.value:
				raise CheckDataError(f"{self} has no conditional tag")
			if not self.positive_responses.value:
				raise CheckDataError(f"{self} has no positive responses")
			block = blocks.add.input_block(
				block_title=self.name,
				element=element,
				dispatch_action=True,
				block_id=str(self.id),
				optional=False,
				action_id=f"checks_conditional__{self.conditional_tag.value}",
				initial_option=self.conditional_tag.value
			)
		else:
			block = blocks.add.input_block(
				block_title=self.name,
				element=element,
				dispatch_action=False,
				block_id=str(self.id),
				optional=False
			)

		return block

	def get_result_column_data(self, result_string):
		# Get the column data for the result string
		if not self.results_column_id.value:
			raise CheckDataError(f"{self} has no results column id")
		column_data = {
			str(self.results_column_id.value): str(result_string)
		}
		if not column_data:
			raise CheckDataError(f"{self} has no column data")
		return column_data


class CheckResultItem(BaseItemType):
	BOARD_ID = 6487504495

	def __init__(self, item_id=None, api_data: dict | None = None, search: bool = False):
		self.main_item_id = columns.TextValue("text__1")

		super().__init__(item_id=item_id, api_data=api_data, search=search)


class CourierDataDumpItem(BaseItemType):
	BOARD_ID = 1031579094

	def __init__(self, item_id=None, api_data: dict | None = None, search: bool = False):
		self.job_id = columns.TextValue("stuart_job_id")
		self.booking_time = columns.DateValue("booking_time6")
		self.allocation_time = columns.DateValue("hour3")
		self.collection_time = columns.DateValue("collection_time4")
		self.delivery_time = columns.DateValue("delivery_time")

		self.cost_inc_vat = columns.NumberValue("cost__ex_vat_")
		self.cost_ex_vat = columns.NumberValue("numbers2")
		self.vat = columns.NumberValue("vat")

		self.collection_postcode = columns.TextValue("collection_postcode5")
		self.delivery_postcode = columns.TextValue("delivery_postcode")

		self.distance = columns.NumberValue("distance")
		self.tracking_url = columns.LinkURLValue("tracking_url")

		self.main_item_id = columns.TextValue("text6")

		self.delivery_id = columns.TextValue("text")

		self.job_status = columns.StatusValue("status")

		super().__init__(item_id=item_id, api_data=api_data, search=search)


class SickWDataItem(BaseItemType):
	BOARD_ID = 5808954740

	def __init__(self, item_id=None, api_data: dict | None = None, search: bool = False):
		self.imeisn = columns.TextValue("text")
		self.model_description = columns.TextValue("text5")
		self.model = columns.TextValue("text0")
		self.serial = columns.TextValue("text8")
		self.fetched_data = columns.TextValue("long_text")

		self.model_matches_connect = columns.ConnectBoards("connect_boards")
		self.model_description_matches_connect = columns.ConnectBoards("board_relation")
		self.main_board_connect = columns.ConnectBoards("connect_boards9")

		self.main_item_id = columns.TextValue("text7")

		super().__init__(item_id=item_id, api_data=api_data, search=search)


class StaffItem(BaseItemType):
	BOARD_ID = 2477606931

	def __init__(self, item_id=None, api_data: dict | None = None, search: bool = False):
		self.monday_id = columns.TextValue("text")
		self.slack_id = columns.TextValue("text8")

		self.internal_hourly_rate = columns.NumberValue("numbers")

		super().__init__(item_id=item_id, api_data=api_data, search=search)


class BatteryTestItem(BaseItemType):
	BOARD_ID = 586351593

	def __init__(self, item_id=None, api_data: dict | None = None, search: bool = False):
		self.start_level = columns.NumberValue("numbers")
		self.end_level = columns.NumberValue("numbers_1")
		self.time_tracking = columns.TimeTrackingColumn("time_tracking")

		self.test_status = columns.StatusValue("status")
		self.test_parameters = columns.DropdownValue("dropdown")

		self.main_item_connect = columns.ConnectBoards("connect_boards")

		super().__init__(item_id=item_id, api_data=api_data, search=search)

	def get_hourly_consumption_rate(self):
		start_level = self.start_level.value
		end_level = self.end_level.value
		difference = start_level - end_level
		seconds = self.time_tracking.value
		if not seconds:
			raise MondayDataError(f"{self} has no time tracking data, cannot calculate consumption rate")

		return difference / (seconds / 3600)


class CheckDataError(MondayDataError):
	pass
