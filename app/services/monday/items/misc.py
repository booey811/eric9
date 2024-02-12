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
