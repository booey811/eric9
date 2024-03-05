from zenpy.lib.api_objects import Comment

from ...services import monday, zendesk, email


def print_quote_to_zendesk(main_id):
	main = monday.items.MainItem(main_id).load_from_api()

	if not main.ticket_id.value:
		raise Exception(f"Main Item {main_id} does not have a Ticket ID")

	ticket = zendesk.client.tickets(id=int(main.ticket_id.value))
	device = monday.items.DeviceItem(main.device_id)
	products = main.products
	user = zendesk.client.users(id=int(ticket.requester_id))
	custom_lines = [monday.items.misc.CustomQuoteLineItem(line) for line in main.custom_quote_connect.value]

	email_generator = email.QuoteEmailGenerator(
		user=user,
		device=device,
		product_list=products,
		custom_quote=custom_lines,
	)

	body = email_generator.get_email()

	ticket.comment = Comment(
		public=False,
		body=body
	)
	zendesk.client.tickets.update(ticket)
	return body