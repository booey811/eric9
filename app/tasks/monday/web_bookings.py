import logging

from zenpy.lib.exception import APIException
from zenpy.lib.api_objects import Ticket, Comment

from ...services import monday, woocommerce, zendesk
from ...models.misc import WebBookingModel
from ...models import ProductModel, MainModel, DeviceModel
from ...errors import EricError
from ...utilities import notify_admins_of_error

log = logging.getLogger('eric')


def transfer_web_booking(web_booking_item_id):
	item = monday.get_items([web_booking_item_id])[0]
	web_booking = WebBookingModel(item.id, item)
	main = MainModel.MONCLI_MODEL(
		name=web_booking.model.name,
		board=monday.client.get_board_by_id(MainModel.BOARD_ID)
	)

	# extract Woo Commerce order data
	woo_order_data = woocommerce.woo.get(f"orders/{web_booking.model.woo_commerce_order_id}")

	if woo_order_data.status_code != 200:
		notify_admins_of_error(
			f"{web_booking} could not find order {web_booking.model.woo_commerce_order_id} in Woo Commerce")
		raise WebBookingTransferError(
			f"{web_booking} could not find order {web_booking.model.woo_commerce_order_id} in Woo Commerce")

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

	prod_board = monday.client.get_board_by_id(2477699024)
	search = prod_board.columns['text3']  # woo commerce product ID column
	search_results = prod_board.get_items_by_multiple_column_values(
		column=search,
		column_values=[str(_['id']) for _ in repair_products],
		get_column_values=True
	)

	if len(search_results) != len(repair_products):
		notify_admins_of_error(
			f"{web_booking} could not find all products in {web_booking.model.woo_commerce_order_id} in Eric")

	products = [ProductModel(_.id, _) for _ in search_results]
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
		device = DeviceModel(device_id)
		email_subject = f"Your {device.model.name} Repair"
	else:
		device = DeviceModel(4028854241)  # defaults to Other Device
		email_subject = "Your Repair with iCorrect"

	main.device_connect = str(device.id)

	# create zendesk ticket
	user_search = zendesk.helpers.search_zendesk(web_booking.model.email)
	if not user_search:
		# no user found, create user
		log.debug(f"No User Found, creating")
		try:
			user = zendesk.helpers.create_user(
				web_booking.model.name,
				web_booking.model.email,
				web_booking.model.phone
			)
		except APIException as e:
			log.debug(f"Could not create user: {e}")
			notify_admins_of_error("Could not create user: " + str(e))
			raise WebBookingTransferError(f"Could not create user: {e}")

	elif len(user_search) == 1:
		user = next(user_search)
	else:
		raise WebBookingTransferError(f"Multiple users found ({len(search_results)}) for {web_booking.model.email}")

	booking_text = f"Website Notes:\n" + web_booking.model.initial_notes

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

	main.email = web_booking.model.email
	main.phone = web_booking.model.phone
	main.ticket_id = str(ticket.id)
	main.ticket_url = {
		'url': str(ticket.url),
		'text': str(ticket.id)
	}
	main.description = "; ".join([f"{p.name}(£{p.price})" for p in products])

	main.point_of_collection = web_booking.model.point_of_collection
	main.address_comment = web_booking.model.address_comment
	main.address_street = web_booking.model.address_street
	main.address_postcode = web_booking.model.address_postcode

	main.save()

	main = MainModel(main.id, main.item)
	main.get_thread('notes').add_reply(booking_text)
	main.print_stock_check()

	return main


class WebBookingTransferError(EricError):
	pass
