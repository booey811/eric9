from moncli.models import MondayModel
from moncli import types as col_type

from .base import BaseEricModel


class _BaseWebBookingModel(MondayModel):
	"""
	Web Booking Model
	"""

	# order data
	woo_commerce_order_id: str = col_type.TextType(id='order_id')
	initial_notes = col_type.TextType(id='notes')
	booking_date = col_type.DateType(id='booking_time', has_time=True)

	# address data
	point_of_collection = col_type.TextType(id='text9')
	address_comment = col_type.TextType(id='company_flat')
	address_street = col_type.TextType(id='street_name_number')
	address_postcode = col_type.TextType(id='post_code')

	# user data
	email = col_type.TextType(id='email')
	phone = col_type.TextType(id='phone_number')

	# payment data
	pay_method = col_type.StatusType(id='payment_method')
	pay_status = col_type.StatusType(id='payment_status')

	# repair data
	service = col_type.StatusType(id='service')


class WebBookingModel(BaseEricModel):
	MONCLI_MODEL = _BaseWebBookingModel

	def __init__(self, item_id, moncli_item=None):
		super().__init__(item_id, moncli_item)

	def __str__(self):
		return f"WebBookingModel({self.id}): {self._name or 'Not Fetched'}"

	@property
	def model(self) -> _BaseWebBookingModel:
		return super().model
