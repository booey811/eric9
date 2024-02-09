from ..api.items import BaseItemType
from ..api import columns


class WebBookingItem(BaseItemType):
	BOARD_ID = 973467694

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
from ....services import typeform


class TypeFormWalkInResponseItem(BaseItemType):
	BOARD_ID = 4752037048

	FORM_ID = "LtNyVqVN"

	phone = columns.TextValue('text')
	email = columns.TextValue('text_1')
	device_type = columns.StatusValue('device_category')
	device = columns.TextValue('device6')
	repair_notes = columns.TextValue('text5')

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
			except KeyError:
				continue

		self.commit()
		return self
