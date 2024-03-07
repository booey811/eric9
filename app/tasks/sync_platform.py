from zenpy.lib.api_objects import Ticket, CustomField, Comment

from ..services.monday import items
from ..services.monday.api.exceptions import MondayDataError
from ..services import zendesk, monday
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
					raise MondayDataError(
						"Cannot convert Booking Date to string, please select which service the client will be using")
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


def sync_to_monday(ticket_id, main_id=''):
	ticket = zendesk.client.tickets(id=ticket_id)
	user = zendesk.client.users(id=ticket.requester_id)

	if user.organization:
		name = f"{user.name} ({user.organization.name})"
	else:
		name = user.name

	if not main_id:
		main_item = items.MainItem().create(name=name, reload=True)
		main_item.notifications_status = 'ON'
		main_item.ticket_id = str(ticket.id)
		main_item.ticket_url = [str(ticket.id), f"https://icorrect.zendesk.com/agent/tickets/{ticket.id}"]
		main_item.email = user.email
		main_item.phone = user.phone or 'No Number Found'
		ticket.custom_fields.append(CustomField(
			id=zendesk.custom_fields.FIELDS_DICT['main_item_id'],
			value=str(main_item.id)
		))
	else:
		main_item = items.MainItem(main_id).load_from_api()

	try:
		# status
		try:
			status_tag = [t for t in ticket.tags if 'repair_status-' in t][0]
			status_index = int(status_tag.split('-')[1])
			status_label = main_item.convert_dropdown_ids_to_labels([status_index], main_item.main_status.column_id)[0]
		except IndexError:
			status_label = "Awaiting Confirmation"

		# client
		try:
			client_tag = [t for t in ticket.tags if 'client-' in t][0]
			client_index = int(client_tag.split('-')[1])
			client_label = main_item.convert_dropdown_ids_to_labels([client_index], main_item.client.column_id)[0]
		except IndexError:
			client_label = "End User"

		# service
		try:
			service_tag = [t for t in ticket.tags if 'service-' in t][0]
			service_index = int(service_tag.split('-')[1])
			service_label = main_item.convert_dropdown_ids_to_labels([service_index], main_item.service.column_id)[0]
		except IndexError:
			service_label = "Unconfirmed"

		# repair type
		try:
			repair_tag = [t for t in ticket.tags if 'repair_type-' in t][0]
			repair_index = int(repair_tag.split('-')[1])
			repair_label = main_item.convert_dropdown_ids_to_labels([repair_index], main_item.repair_type.column_id)[0]
		except IndexError:
			repair_label = "Repair"

		# imeisn
		imei_field_id = zendesk.custom_fields.FIELDS_DICT['imeisn']
		imeisn = None
		for cf in ticket.custom_fields:
			if cf['id'] == imei_field_id:
				imeisn = cf['value']
				break

		# passcode
		pc_field_id = zendesk.custom_fields.FIELDS_DICT['passcode']
		passcode = None
		for cf in ticket.custom_fields:
			if cf['id'] == pc_field_id:
				passcode = cf['value']
				break

		# device id
		try:
			device_tag = [t for t in ticket.tags if 'device__' in t][0]
			device_id = int(device_tag.split('__')[1])
		except IndexError:
			device_id = 4028854241  # other device

		# product ids
		product_ids = [int(t.split('__')[1]) for t in ticket.tags if 'product__' in t]

		def determine_address():
			# fetch from ticket
			_notes = ''
			_street = ''
			_postcode = ''

			ticket_street = None
			ticket_post = None
			ticket_notes = None

			for f in ticket.custom_fields:
				if f['id'] == 360006582778:  # street
					ticket_street = cf['value']
					break

			for f in ticket.custom_fields:
				if f['id'] == 360006582758:  # postcode
					ticket_post = cf['value']
					break

			for f in ticket.custom_fields:
				if f['id'] == 360006582798:  # address notes
					ticket_notes = cf['value']
					break

			# fetch from user
			requester = ticket.requester
			requester_street = requester.user_fields['street_address']
			requester_post = requester.user_fields['post_code']
			requester_notes = requester.user_fields['company_flat_number']

			org = requester.organization
			if org:
				org_street = org.organization_fields['street_address']
				org_post = org.organization_fields['postcode']
				org_notes = org.organization_fields['company_flat_number']
			else:
				org_street = ""
				org_post = ""
				org_notes = ""

			_street = ticket_street or requester_street or org_street
			_postcode = ticket_post or requester_post or org_post
			_notes = ticket_notes or requester_notes or org_notes

			return [_notes, _street, _postcode]

		address_notes, address_street, address_postcode = determine_address()

		main_item.main_status = status_label
		main_item.client = client_label
		main_item.service = service_label
		main_item.repair_type = repair_label
		if imeisn:
			main_item.imeisn = imeisn
		if passcode:
			main_item.passcode = passcode
		main_item.address_notes = address_notes
		main_item.address_street = address_street
		main_item.address_postcode = address_postcode
		main_item.device_id = device_id
		main_item.products_connect = product_ids

		main_item.commit()
		zendesk.client.tickets.update(ticket)
	except Exception as e:
		ticket.status = 'open'
		ticket.comment = Comment(
			public=False,
			body=f"Could not sync to Monday: {e}"
		)
		raise e
