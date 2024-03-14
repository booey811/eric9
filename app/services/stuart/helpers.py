import datetime
import json

from zenpy.lib.api_objects import CustomField

import config
from ...services import monday

conf = config.get_config()


def generate_address_string(address_notes, address_street, address_postcode):
	if address_notes:
		return f"{address_notes}, {address_street}, {address_postcode}"
	else:
		return f"{address_street}, {address_postcode}"


def generate_job_data(main_board_item: monday.items.MainItem, direction):
	if main_board_item.booking_date.value:
		time = main_board_item.booking_date.value.isoformat()
	else:
		time = None

	icorrect_contact = {
		"firstname": conf.ICORRECT_ADDRESS_INFO['collection_contact'].split()[0],
		"lastname": conf.ICORRECT_ADDRESS_INFO['collection_contact'].split()[0],
		"phone": "+442070998517",
		"email": "couriers@icorrect.co.uk",
		"company": "iCorrect"
	}
	client_contact = {
		"firstname": main_board_item.name,
		"phone": main_board_item.phone.value,
		"email": main_board_item.email.value,
	}

	if main_board_item.company_name.value:
		client_contact['company'] = main_board_item.company_name.value

	if direction == 'incoming':
		collect_address = generate_address_string(
			main_board_item.address_notes.value,
			main_board_item.address_street.value,
			main_board_item.address_postcode.value
		)
		collect_comment = main_board_item.address_notes.value or "No Collection Notes"
		collect_contact = client_contact
		deliver_address = "iCorrect, 12 Margaret Street, W1W8JQ"
		deliver_comment = "Please deliver to the reception"
		deliver_contact = icorrect_contact
	elif direction == 'outgoing':
		collect_address = "iCorrect, 12 Margaret Street, W1W8JQ"
		collect_comment = "Please collect from the reception"
		collect_contact = icorrect_contact

		deliver_address = generate_address_string(
			main_board_item.address_notes.value,
			main_board_item.address_street.value,
			main_board_item.address_postcode.value
		)
		deliver_comment = main_board_item.address_notes.value or "No Delivery Notes "
		deliver_contact = client_contact
	else:
		raise ValueError(f"Invalid Direction: {direction}")

	basic = {
		"job": {
			"pickups": [
				{
					"address": collect_address,
					"comment": collect_comment,
					"contact": collect_contact
				}
			],
			"dropoffs": [
				{
					"package_type": "small",
					"address": deliver_address,
					"comment": deliver_comment,
					"contact": deliver_contact,
				}
			]
		}
	}

	if time and direction == 'incoming':
		basic['pickup_at'] = time

	return basic