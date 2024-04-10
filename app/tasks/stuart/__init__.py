import datetime
import json

from zenpy.lib.api_objects import CustomField

from ...services import monday, stuart, zendesk
from ...utilities import notify_admins_of_error


def book_courier(main_id, direction):
	"""Book a collection for a main item"""
	main_item = monday.items.MainItem(main_id).load_from_api()
	try:
		log_item = monday.items.misc.CourierDataDumpItem().create(f"{main_item.name}: {direction.capitalize()} Booking")
	except Exception as e:
		notify_admins_of_error(f"Could Not Create Courier Log with name {main_item.name}: {e}")
		name = main_item.name.replace('/', '').replace('"', '').replace("-", "")
		log_item = monday.items.misc.CourierDataDumpItem().create(f"{name}: {direction.capitalize()} Booking")
	try:
		try:
			job_data = stuart.helpers.generate_job_data(main_item, direction, client_reference=str(log_item.id))
		except Exception as e:
			main_item.add_update(f"Could not generate job data: {e}", main_item.error_thread_id)
			monday.api.monday_connection.items.delete_item_by_id(log_item.id)
			raise e
		try:
			response = stuart.client.create_job(job_data)
			response = response.json()
		except Exception as e:
			main_item.add_update(f"Could not create job: {e}", main_item.error_thread_id)
			raise e
		log_job_data(job_data, response, main_item, log_item)
		if direction == 'incoming':
			main_item.be_courier_collection = 'Booking Complete'
		elif direction == 'outgoing':
			main_item.be_courier_return = 'Booking Complete'
		try:
			ticket = zendesk.client.tickets(id=int(main_item.ticket_id.value))
			custom_field_id = zendesk.custom_fields.FIELDS_DICT['tracking_link']
			ticket.custom_fields.append(CustomField(
				id=int(custom_field_id),
				value=str(response['deliveries'][0]['tracking_url'])
			))
			zendesk.client.tickets.update(ticket)
		except Exception as e:
			main_item.add_update(f"Courier Booked, but could not update ticket with tracking link: {e}", main_item.error_thread_id)
			raise e
		main_item.commit()

	except Exception as e:
		notify_admins_of_error(e)
		if direction == 'incoming':
			main_item.be_courier_collection = 'Booking Failed'
		elif direction == 'outgoing':
			main_item.be_courier_return = 'Booking Failed'
		main_item.main_status = "Error"
		notify_admins_of_error(f"Error booking courier for {str(main_item)}: {e}")
		main_item.commit()
		raise e


def log_job_data(booking_data, stuart_response, main_item, log_item: "monday.items.misc.CourierDataDumpItem" = None):
	"""Log the job data"""

	try:
		if not log_item:
			log_item = monday.items.misc.CourierDataDumpItem()

		job_id = str(stuart_response.get('id'))
		if job_id:
			log_item.job_id = job_id

		delivery_id = stuart_response['deliveries'][0]['id']

		log_item.cost_inc_vat = stuart_response['pricing']['price_tax_included']
		log_item.cost_ex_vat = stuart_response['pricing']['price_tax_excluded']
		log_item.vat = stuart_response['pricing']['tax_amount']

		log_item.collection_postcode = stuart_response['deliveries'][0]['pickup']['address']['postcode']
		log_item.delivery_postcode = stuart_response['deliveries'][0]['dropoff']['address']['postcode']
		log_item.distance = stuart_response['distance']
		log_item.tracking_url = ["Tracking", stuart_response['deliveries'][0]['tracking_url']]
		log_item.main_item_id = str(main_item.id)

		log_item.delivery_id = str(delivery_id)

		if not log_item.id:
			log_item.create(main_item.name)
		else:
			log_item.commit()

		log_item.add_update(f"=== REQUEST DATA ===\n\n{json.dumps(booking_data, indent=4)}")
		log_item.add_update(f"=== RESPONSE DATA ===\n\n{json.dumps(stuart_response, indent=4)}")

		return log_item

	except Exception as e:
		notify_admins_of_error(e)
		raise e


def handle_webhook_update(courier_item_id):
	"""Handle a webhook update from Stuart, currently only used for confirming deliveries"""
	try:
		try:
			log_item = monday.items.misc.CourierDataDumpItem(courier_item_id).load_from_api()
		except Exception as e:
			raise monday.api.exceptions.MondayDataError(f"Could not load courier item with id {courier_item_id}: {e}")

		main_id = log_item.main_item_id.value
		if not main_id:
			raise monday.api.exceptions.MondayDataError(f"Could not find main item id for job_id {job_id}")

		main_item = monday.items.MainItem(main_id).load_from_api()

		if main_item.main_status.value == "Courier Booked":
			main_item.main_status = "Received"
			main_item.commit()
		elif main_item.main_status.value == "Return Booked":
			main_item.main_status = "Returned"
			main_item.commit()
		else:
			raise monday.api.exceptions.MondayDataError("Could Not Update Main Item Status")

	except Exception as e:
		notify_admins_of_error(f"Stuart Webhook Update: {e}")
		raise e
