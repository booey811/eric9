from zenpy.lib.api_objects import Ticket, CustomField, Comment

from ..services.monday import items
from ..services.monday.api.exceptions import MondayDataError
from ..services import zendesk
from ..utilities import notify_admins_of_error

field_ids = zendesk.custom_fields.FIELDS_DICT


def sync_to_zendesk(main_item_id, ticket_id):
	try:
		main_item = items.MainItem(main_item_id).load_from_api()
	except Exception as e:
		raise e

	try:
		ticket = zendesk.client.tickets(id=ticket_id)
	except Exception as e:
		raise e

	failed = []

	try:
		# convert to zendesk tags
		# main status, client, service, repair type, device, products

		tags = ticket.tags
		# main status
		try:
			index = main_item.main_status.get_label_conversion_dict(main_item.BOARD_ID)[main_item.main_status.value]
		except MondayDataError:
			index = 0  # awaiting confirmation index
			failed.append(['MainStatus', main_item.main_status.value])
		tags.append(f"repair_status-{index}")

		# client
		try:
			index = main_item.client.get_label_conversion_dict(main_item.BOARD_ID)[main_item.client.value]
		except MondayDataError:
			index = 5  # unconfirmed index
			failed.append(['Client', main_item.client.value])
		tags.append(f"client-{index}")

		# service
		try:
			index = main_item.service.get_label_conversion_dict(main_item.BOARD_ID)[main_item.service.value]
		except MondayDataError:
			index = 0
			failed.append(['Service', main_item.service.value])
		tags.append(f"service-{index}")

		# repair type
		try:
			index = main_item.repair_type.get_label_conversion_dict(main_item.BOARD_ID)[main_item.repair_type.value]
		except MondayDataError:
			index = 0
			failed.append(['RepairType', main_item.repair_type.value])
		tags.append(f"repair_type-{index}")

		# device
		if main_item.device_id:
			tags.append(f"device__{main_item.device_id}")

		if main_item.products_connect.value:
			for t in tags:
				if 'product__' in t:
					tags.remove(t)
			for product_id in main_item.products_connect.value:
				tags.append(f"product__{product_id}")

		# sync text fields:
		# address notes, street address, postcode, imei/sn, passcode, booking date string

		# address notes
		if main_item.address_notes.value:
			ticket.custom_fields.append(
				CustomField(
					id=field_ids['address_notes'],
					value=main_item.address_notes.value
				)
			)

		# street address
		if main_item.address_street.value:
			ticket.custom_fields.append(
				CustomField(
					id=field_ids['address_street'],
					value=main_item.address_street.value
				)
			)

		# postcode
		if main_item.address_postcode.value:
			ticket.custom_fields.append(
				CustomField(
					id=field_ids['address_postcode'],
					value=main_item.address_postcode.value
				)
			)

		# imei/sn
		if main_item.imeisn.value:
			ticket.custom_fields.append(
				CustomField(
					id=field_ids['imeisn'],
					value=main_item.imeisn.value
				)
			)

		# passcode
		if main_item.passcode.value:
			ticket.custom_fields.append(
				CustomField(
					id=field_ids['passcode'],
					value=main_item.passcode.value
				)
			)

		# booking date string
		ds = "as soon as possible"
		if main_item.booking_date.value:
			try:
				if not main_item.service.value:
					raise MondayDataError("Cannot convert Booking Date to string, please select which service the client will be using")
				if 'mail' in main_item.service.value.lower():
					# mail format: on Wednesday 14th February
					ds = main_item.booking_date.value.strftime("on %A %d %B")
				else:
					# courier format: "at 12:30PM on Wednesday 14 February"
					ds = main_item.booking_date.value.strftime("at %I:%M%p on %A %d %B")
			except MondayDataError as e:
				failed.append(['BookingDateString (Service Issue)', main_item.service.value])
				raise e
			except Exception as e:
				failed.append(['BookingDateString', main_item.booking_date.value])
				notify_admins_of_error(str(e))
				raise e
		ticket.custom_fields.append(
			CustomField(
				id=field_ids['booking_date_string'],
				value=ds
			)
		)

		if failed:
			message = f"{str(main_item)}Failed Monday -> Zendesk sync, could not locate labels\n\n"
			for f in failed:
				message += f"{f[0]}: {f[1]}\n"
			notify_admins_of_error(message)

		ticket = zendesk.client.tickets.update(ticket).ticket

	except Exception as e:
		message = f"Error syncing to Zendesk: {e}\n\n"
		for f in failed:
			message += f"{f[0]}: {f[1]}\n"
		ticket.comment = Comment(
			public=False,
			body=message
		)
		ticket.status = 'open'
		ticket = zendesk.client.tickets.update(ticket).ticket
		main_item.add_update(message, main_item.notes_thread_id.value)
		notify_admins_of_error(message)

	return ticket
