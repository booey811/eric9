import logging
import datetime

from zenpy.lib.exception import APIException
from zenpy.lib.api_objects import Ticket, Comment

import app.services.monday.api.client
from ...services import monday, woocommerce, zendesk
from ...errors import EricError
from ...utilities import notify_admins_of_error
from ...services.monday.api.client import get_api_items
from ...tasks.sync_platform import sync_to_zendesk
import config

conf = config.get_config()

log = logging.getLogger('eric')


def transfer_web_booking(web_booking_item_id):
	def check_booking_date(booking_date: datetime.datetime, zen_ticket):
		"""checks booking date to see if it is a day we are open. First check will be weekend, the another check will
		occur that checks if the date is within a public holiday (hard coded)"""

		class CannotAllowBooking(EricError):
			def __init__(self, reason, z_ticket: Ticket):
				self._reason = reason
				self.ticket = z_ticket
				if reason == 'weekend':
					# https://icorrect.zendesk.com/admin/workspaces/agent-workspace/macros/15599429837073
					self.macro_id = "15599429837073"
				elif reason == 'bank_holiday':
					# https://icorrect.zendesk.com/admin/workspaces/agent-workspace/macros/15599487893009
					self.macro_id = "15599487893009"
				elif reason == 'same_day_mail_in':
					# https://icorrect.zendesk.com/admin/workspaces/agent-workspace/macros/12326605824017
					self.macro_id = "12326605824017"
				elif reason == 'booking_is_tomorrow':
					# https://icorrect.zendesk.com/admin/workspaces/agent-workspace/macros/17136218174481
					self.macro_id = "17136218174481"
				elif reason == 'collection_in_afternoon':
					# https://icorrect.zendesk.com/admin/workspaces/agent-workspace/macros/17137297912593
					self.macro_id = '17137297912593'
				elif reason == 'icorrect_holiday':
					# https://icorrect.zendesk.com/admin/workspaces/agent-workspace/macros/21046931205137
					self.macro_id = '21046931205137'
				else:
					raise ValueError(
						f"CannotAllowBooking must be used with 'collection_in_afternoon', 'booking_is_tomorrow', 'bank_holiday' or 'weekend', not {reason}")

				self._send_macro()

			def __str__(self):
				return f"Cannot Proceed with Booking: {self._reason}"

			def _send_macro(self):
				r = zendesk.client.tickets.show_macro_effect(self.ticket, self.macro_id)
				zendesk.client.tickets.update(r.ticket)

		# ensure dt is a date
		try:
			date = booking_date.date()
		except AttributeError:
			date = booking_date

		# check for weekend
		if date.isoweekday() > 5:  # 4 == Friday, 5 == Saturday, 6 == Sunday
			# we are not open on selected date as it's a weekend, raise error
			raise CannotAllowBooking('weekend', zen_ticket)
		else:
			# continue to next check
			pass

		# check for public holiday
		for holiday in conf.PUBLIC_HOLIDAYS:
			if holiday == date:
				# date is a public holiday, raise error
				raise CannotAllowBooking('bank_holiday', zen_ticket)
			else:
				# date is not a public holiday, proceed as normal
				pass

		# check for icorrect holiday closure
		for holiday in conf.ICORRECT_HOLIDAYS:
			if holiday == date:
				# date is a date that we are closed for
				raise CannotAllowBooking('icorrect_holiday', zen_ticket)
			else:
				# proceed as normal
				pass

		# mail-in checks
		if 'mail' in main.service.value.lower():

			# check for same-day RM booking
			today = datetime.datetime.today().date()
			if today == booking_date:
				raise CannotAllowBooking('same_day_mail_in', zen_ticket)

			# check for post-8pm booking for the following day
			now = datetime.datetime.now()
			cutoff = 19
			date_diff = date - now.date()
			if now.hour > cutoff and date_diff.days == 1:  # after 8pm, booking date is tomorrow
				raise CannotAllowBooking('booking_is_tomorrow', zen_ticket)

			# check whether collection is booked for the afternoon
			if booking_date.hour > 13:  # booking date is after 1pm
				raise CannotAllowBooking('collection_in_afternoon', zen_ticket)

		return True

	item = get_api_items([web_booking_item_id])[0]
	web_booking = monday.items.misc.WebBookingItem(item['id'], item)
	main = monday.items.MainItem()

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

	search_results = []

	try:
		for _ in repair_products:
			try:
				results = monday.items.ProductItem(search=True).search_board_for_items(
					'woo_commerce_product_id',
					str(_['id'])
				)
				result = results[0]
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

	def determine_ticket_tags():

		tag_results = [
			"web_booking",
			f"device__{device_id}",
		]

		for prod in products:
			tag_results.append("product__" + str(prod.id))

		return tag_results

	ticket = Ticket(
		subject=email_subject,
		description=email_subject,
		comment=Comment(
			body=booking_text,
			public=False
		),
		requester_id=user.id,
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

	main.add_update(booking_text, main.notes_thread_id.value)
	main.add_update(main.get_stock_check_string([str(p.id) for p in products]), main.notes_thread_id.value)

	sync_to_zendesk(main.id, ticket.id)

	check_booking_date(web_booking.booking_date.value, ticket)

	return main


def transfer_type_form_booking(type_form_booking_item_id):

	item = get_api_items([type_form_booking_item_id])[0]
	type_form_booking = monday.items.misc.TypeFormWalkInResponseItem(item['id'], item)
	main = monday.items.MainItem()


class WebBookingTransferError(EricError):
	pass
