import logging

from zenpy.lib.exception import APIException
from zenpy.lib.api_objects import Ticket, Comment

import app.services.monday.api.client
from ...services import monday, woocommerce, zendesk
from ...errors import EricError
from ...utilities import notify_admins_of_error
from ...services.monday.api.client import get_api_items

log = logging.getLogger('eric')


def transfer_web_booking(web_booking_item_id):
	item = get_api_items([web_booking_item_id])[0]
	web_booking = monday.items.misc.WebBookingItem(item['id'], item)
	main = monday.items.MainItem(None)

	# extract Woo Commerce order data
	woo_order_data = woocommerce.woo.get(f"orders/{web_booking.woo_commerce_order_id.value}")

	if woo_order_data.status_code != 200:
		notify_admins_of_error(
			f"{web_booking} could not find order {web_booking.woo_commerce_order_id} in Woo Commerce")
		raise WebBookingTransferError(
			f"{web_booking} could not find order {web_booking.woo_commerce_order_id} in Woo Commerce")

	woo_order_data = woo_order_data.json()

	woo_commerce_product_ids = [str(line['product_id']) for line in woo_order_data['line_items']]
	woo_commerce_product_data = woocommerce.woo.get(
		f"products/",
		params={
			'include': ','.join(woo_commerce_product_ids)
		}
	)

	if woo_commerce_product_data.status_code != 200:
		notify_admins_of_error(
			f"{web_booking} failed to retrieve anything from Woo Commerce: {woo_commerce_product_data.text}"
		)
		raise WebBookingTransferError(
			f"{web_booking} failed to retrieve anything from Woo Commerce: {woo_commerce_product_data.text}"
		)

	if len(woo_commerce_product_ids) != len(woo_commerce_product_data.json()):
		log.warning = f"{web_booking} could not find all products in {web_booking.model.woo_commerce_order_id} in Woo Commerce"
		notify_admins_of_error(
			f"{web_booking} could not find all products in {web_booking.model.woo_commerce_order_id} in Woo Commerce"
		)

	woo_commerce_product_data = woo_commerce_product_data.json()

	service_products = []
	repair_products = []

	for wp in woo_commerce_product_data:
		log.debug("WooProduct: " + str(wp))
		category_id = str(wp['categories'][0]['id'])
		if category_id == '582':
			service_products.append(wp)
		else:
			repair_products.append(wp)

	if len(service_products) != 1:
		notify_admins_of_error(
			f"{web_booking} could not find a service product: {woo_commerce_product_data}"
		)
		service = 'Unconfirmed'
	elif 'national courier' in service_products[0]['name'].lower():
		service = 'Mail-In'
	elif 'london courier' in service_products[0]['name'].lower():
		service = 'Stuart Courier'
	elif 'walk' in service_products[0]['name'].lower():
		service = 'Walk-In'
	else:
		raise WebBookingTransferError(f'{str(web_booking)} could not determine service type')

	main.service = service

	search_prod = monday.items.ProductItem(None)

	search_results = []

	try:
		for _ in repair_products:
			try:
				result = search_prod.search_board_for_items('woo_commerce_product_id', str(_['id']))[0]
				search_results.append(monday.items.ProductItem(result['id'], result))
			except IndexError:
				log.error(f"{web_booking} could not find Woo product in Eric: {str(_['name'])}({str(_['id'])})")

	except Exception as e:
		notify_admins_of_error(f"Could Not Fetch Products for Web Booking: {e}")

	if len(search_results) != len(repair_products):
		notify_admins_of_error(
			f"{web_booking} could not find all products in {web_booking.woo_commerce_order_id} in Eric")

	products = search_results
	main.products_connect = [str(_.id) for _ in products]

	repair_type = 'Repair'
	for p in products:
		if 'diagnostic' in p.name.lower():
			repair_type = 'Diagnostic'
			break

	main.repair_type = repair_type

	device_ids = [p.device_id for p in products if p.device_id is not None]
	device_id = device_ids[0] if device_ids else None
	if device_id:
		d_id = device_id
		device_data = app.services.monday.api.client.get_api_items([d_id])[0]
		device = monday.items.DeviceItem(device_data['id'], device_data)
		email_subject = f"Your {device.name} Repair"
	else:
		device_id = 4028854241  # Other Device
		email_subject = "Your Repair with iCorrect"

	main.device_id = int(device_id)

	# create zendesk ticket
	user_search = zendesk.helpers.search_zendesk(str(web_booking.email.value))
	if not user_search:
		# no user found, create user
		log.debug(f"No User Found, creating")
		try:
			user = zendesk.helpers.create_user(
				web_booking.name,
				web_booking.email.value,
				web_booking.phone.value
			)
		except APIException as e:
			log.debug(f"Could not create user: {e}")
			notify_admins_of_error("Could not create user: " + str(e))
			raise WebBookingTransferError(f"Could not create user: {e}")

	elif len(user_search) == 1:
		user = next(user_search)
	else:
		raise WebBookingTransferError(f"Multiple users found ({len(search_results)}) for {web_booking.model.email}")

	booking_text = f"Website Notes:\n" + web_booking.booking_notes.value

	ticket = Ticket(
		subject=email_subject,
		description=email_subject,
		comment=Comment(
			body=booking_text,
			public=False
		),
		requester_id=user.id,
		tags=['web_booking']
	)

	ticket = zendesk.client.tickets.create(ticket).ticket

	main.email = web_booking.email.value
	main.phone = web_booking.phone.value
	main.ticket_id = str(ticket.id)
	main.ticket_url = [
		str(ticket.id),
		f"https://icorrect.zendesk.com/agent/tickets/{ticket.id}",
	]
	main.description = "; ".join([f"{p.name}(£{p.price})" for p in products])

	main.point_of_collection = web_booking.point_of_collection.value
	main.address_notes = web_booking.address_notes.value
	main.address_street = web_booking.address_street.value
	main.address_postcode = web_booking.address_postcode.value
	main.booking_date = web_booking.booking_date.value
	main.payment_status = web_booking.pay_status.value
	main.payment_method = web_booking.pay_method.value

	main.client = 'End User'
	main.main_status = 'Awaiting Confirmation'
	main.notifications_status = 'ON'

	main.create(web_booking.name)
	main_data = app.services.monday.api.client.get_api_items([main.id])[0]
	main = monday.items.MainItem(main_data['id'], main_data)

	main.add_update(main.get_stock_check_string(), main.notes_thread_id.value)

	return main


class WebBookingTransferError(EricError):
	pass
