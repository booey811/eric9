import datetime

from zenpy.lib.api_objects import Comment

from ...services import monday, zendesk, xero
from ... import tasks


def generate_draft_invoice_for_ticket(ticket_id):
	ticket = zendesk.client.tickets(id=int(ticket_id))
	ticket.tags.remove('inv_generation_requested')
	ticket.status = 'open'
	try:
		# remove any existing invoices linked to this ticket, if they have been marked as sent
		# this is to prevent duplicate invoices being generated
		try:
			inv_id_field = \
			[x for x in ticket.custom_fields if x['id'] == zendesk.custom_fields.FIELDS_DICT['xero_invoice_id']][0]
		except IndexError:
			raise ValueError("Ticket does not have a Xero Invoice ID field")

		inv_id = inv_id_field['value']
		if inv_id:
			invoice = xero.client.get_invoice_by_id(inv_id)
			if invoice:
				if invoice['Status'] == 'DRAFT':
					invoice['Status'] = 'DELETED'
					xero.client.update_invoice(invoice)
				else:
					raise ValueError(f"Invoice is not in DRAFT status, cannot delete it. Status is {invoice['Status']}")

		main_item_search = monday.api.monday_connection.items.fetch_items_by_column_value(
			board_id=monday.items.MainItem.BOARD_ID,
			column_id="text6",
			value=str(ticket_id)
		)
		if main_item_search.get("error_message"):
			raise monday.api.exceptions.MondayAPIError(
				f"Error searching Main Board for Ticket {ticket_id}: {main_item_search['error_message']}")

		results = main_item_search['data']['items_page_by_column_values']['items']

		if len(results) != 1:
			raise ValueError(f"Expected 1 Main Item for Ticket {ticket_id}, found {len(results)}")

		main_item = monday.items.MainItem(results[0]['id'], results[0])
		device = monday.items.DeviceItem(main_item.device_id)

		issue_date = datetime.datetime.now()
		due_date = issue_date

		contact = xero.client.get_contact_by_email(ticket.requester.email)
		if len(contact) > 1:
			raise ValueError(f"Expected 1 Xero Contact for {ticket.requester.email}, found {len(contact)}")
		elif len(contact) < 1:
			# create a new contact

			street_address = main_item.address_street.value or main_item.address_notes.value
			postal_code = main_item.address_postcode.value

			contact = xero.client.create_contact(
				name=ticket.requester.name,
				email=ticket.requester.email,
				street_address=street_address,
				postal_code=postal_code
			)
			contact_id = contact['ContactID']
		else:
			contact_id = contact[0]['ContactID']

		description = f"Service for {device.name}"
		description += f"\nSN/IMEI: {main_item.imeisn.value or 'N/A'}"
		total = 0

		for prod in main_item.products:
			name = prod.name
			description += f"\n{name.replace(device.name, '').strip()}"
			total += prod.price.value

		if main_item.custom_quote_connect.value:
			api_data = monday.api.get_api_items(main_item.custom_quote_connect.value)
			customs = [monday.items.misc.CustomQuoteLineItem(x['id'], x) for x in api_data]
			for custom in customs:
				description += f"\n{custom.name.replace(device.name, '').strip()}"
				total += custom.price.value

		line_items = [xero.client.make_line_item(
			description=description,
			quantity=1,
			unit_amount=total,
			account_code="200",
			line_amount_types="Inclusive",
		)]

		invoice = xero.client.create_invoice(
			contact_id=contact_id,
			issue_date=issue_date,
			due_date=due_date,
			line_items=line_items,
			reference=f"{device.name} Repair",
			line_amount_types="Inclusive"
		)

		ticket.custom_fields.append({
			"id": zendesk.custom_fields.FIELDS_DICT['xero_invoice_id'],
			"value": invoice['InvoiceID']
		})

		inv_summary = """====== INVOICE DRAFTED ======
		Please check the summary below. If correct, please use the 'Confirm Invoice' macro to send receive a link for online payment.\n\n"""

		zen_total = 0
		for line in line_items:
			inv_summary += f"{line['Description']}\n"
			zen_total += int(line['UnitAmount'])

		inv_summary += f"\n\nTotal: £{zen_total}"

		ticket.comment = Comment(
			public=False,
			body=inv_summary
		)

		zendesk.client.tickets.update(ticket)

		return invoice

	except Exception as e:
		body = f"Error Generating Invoice: {e}"
		comment = Comment(public=False, body=body)
		ticket.comment = comment
		zendesk.client.tickets.update(ticket)
		raise e


def confirm_invoice(ticket_id):
	ticket = zendesk.client.tickets(id=int(ticket_id))
	try:
		ticket.tags.remove('confirm_invoice')
	except ValueError:
		# tag not present
		pass
	ticket.status = 'open'
	try:
		inv_id_field = \
		[x for x in ticket.custom_fields if x['id'] == zendesk.custom_fields.FIELDS_DICT['xero_invoice_id']][0]
		inv_id = inv_id_field['value']
		if not inv_id:
			raise ValueError("Ticket does not have a Xero Invoice ID field")

		invoice = xero.client.get_invoice_by_id(inv_id)
		if not invoice:
			raise ValueError(f"No Invoice found with ID {inv_id}, please use the 'Draft Invoice Macro First'")

		if invoice['Status'] == 'DRAFT':
			invoice['Status'] = 'SUBMITTED'
			xero.client.update_invoice(invoice)
		else:
			raise ValueError(f"Invoice is not in DRAFT status, cannot confirm it. Status is {invoice['Status']}")

		edit_url = f"https://go.xero.com/app/!TYR2Z/invoicing/edit/{invoice['InvoiceID']}"
		payment_url = xero.client.get_payment_url(invoice['InvoiceID'])

		ticket.comment = Comment(
			public=False,
			body=f"====== INVOICE CONFIRMED ======\n\nPay Invoice Link: {payment_url}\n\nEdit Invoice Link: {edit_url}"
		)
		zendesk.client.tickets.update(ticket)

		return invoice

	except Exception as e:
		body = f"Error Generating Invoice: {e}"
		comment = Comment(public=False, body=body)
		ticket.comment = comment
		zendesk.client.tickets.update(ticket)
		raise e
