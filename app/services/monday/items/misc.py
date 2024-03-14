import time
import json

from zenpy.lib.api_objects import Ticket, CustomField, Comment

from ..api.items import BaseItemType, BaseCacheableItem
from ..api import columns, get_api_items, exceptions, monday_connection
from ..api.exceptions import MondayDataError
from ... import typeform
from ..items import MainItem
from ...zendesk import helpers, client as zendesk_client, custom_fields


class WebBookingItem(BaseItemType):
	BOARD_ID = 973467694

	transfer_status = columns.StatusValue("status_18")

	woo_commerce_order_id = columns.TextValue('order_id')

	pay_status = columns.StatusValue("payment_status")
	pay_method = columns.StatusValue("payment_method")

	booking_notes = columns.TextValue('notes')
	secondary_notes = columns.LongTextValue('enquiry')

	phone = columns.TextValue('phone_number')
	email = columns.TextValue('email')

	service = columns.StatusValue('service')
	client = columns.StatusValue('client')
	repair_type = columns.StatusValue('type')

	booking_date = columns.DateValue('booking_time')

	address_postcode = columns.TextValue('post_code')
	address_notes = columns.TextValue('company_flat')
	address_street = columns.TextValue('street_name_number')
	point_of_collection = columns.TextValue('text9')


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

		super().__init__(item_id=item_id, api_data=api_data, search=search)


class TypeFormWalkInResponseItem(BaseItemType):
	BOARD_ID = 4752037048

	FORM_ID = "LtNyVqVN"

	phone = columns.TextValue('text')
	email = columns.TextValue('text_1')
	device_type = columns.StatusValue('device_category')
	device = columns.TextValue('device6')
	repair_notes = columns.TextValue('text7')
	push_to_slack = columns.StatusValue('status6')

	def sync_typeform_data(self):

		def get_answer_by_field_id(f_id):
			return [ans for ans in most_recent['answers'] if ans['field']['ref'] == f_id][0]

		typeform_field_refs = {
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

	def __init__(self, item_id=None, api_data: dict | None = None, search: bool = False):
		self.set_type = columns.StatusValue('status9')
		self.pre_check_items_connect = columns.ConnectBoards('connect_boards4')

		self._pre_check_items = None

		super().__init__(item_id=item_id, api_data=api_data, search=search)

	def cache_key(self):
		return "pre_check_set:" + str(self.id)

	def prepare_cache_data(self):
		return {
			"name": str(self.name),
			"id": str(self.id),
			"set_type": self.set_type.value,
			"pre_check_item_ids": self.pre_check_items_connect.value
		}

	def load_from_cache(self, cache_data=None):
		if cache_data is None:
			cache_data = self.fetch_cache_data()
		self.set_type.value = cache_data['set_type']
		self.pre_check_items_connect.value = cache_data['pre_check_item_ids']
		self.id = cache_data['id']
		self.name = cache_data['name']
		return self

	def get_pre_check_items(self):
		if not self.pre_check_items_connect.value:
			self.load_from_api()
		if not self.pre_check_items_connect.value:
			raise exceptions.MondayDataError(f"{self} could not load pre check items: {self._api_data}")
		self._pre_check_items = [PreCheckItem(i['id'], i) for i in get_api_items(self.pre_check_items_connect.value)]
		return self._pre_check_items


class PreCheckItem(BaseCacheableItem):

	BOARD_ID = 4455646189

	def __init__(self, item_id=None, api_data: dict | None = None, search: bool = False):
		self.available_responses = columns.DropdownValue('dropdown')
		self.check_sets_connect = columns.ConnectBoards('board_relation')

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
				raise MondayDataError(f"{self} could not load available responses: {self._api_data}")
		if labels:
			labels = self.convert_dropdown_ids_to_labels(result_ids, self.available_responses.column_id)
			return labels
		else:
			return result_ids


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

		self.job_status = columns.StatusValue("status")

		super().__init__(item_id=item_id, api_data=api_data, search=search)


