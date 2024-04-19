import logging
import datetime
import time
from dateutil.parser import parse
import json

from zenpy.lib.exception import APIException
from zenpy.lib.api_objects import Ticket, Comment, User

import app.services.monday.api.client
from ...services import monday, woocommerce, zendesk, openai
from ...errors import EricError
from ...utilities import notify_admins_of_error
from ...services.monday.api.client import get_api_items
from ...tasks.sync_platform import sync_to_zendesk
import config

conf = config.get_config()

log = logging.getLogger('eric')


def transfer_web_booking(web_booking_item_id):
	def send_confirmation_email():
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
			raise CannotAllowBooking('weekend', ticket)
		else:
			# continue to next check
			pass

		# check for public holiday
		for holiday in conf.PUBLIC_HOLIDAYS:
			if holiday == date:
				# date is a public holiday, raise error
				raise CannotAllowBooking('bank_holiday', ticket)
			else:
				# date is not a public holiday, proceed as normal
				pass

		# check for icorrect holiday closure
		for holiday in conf.ICORRECT_HOLIDAYS:
			if holiday == date:
				# date is a date that we are closed for
				raise CannotAllowBooking('icorrect_holiday', ticket)
			else:
				# proceed as normal
				pass

		# mail-in checks
		if 'mail' in main.service.value.lower():

			# check for same-day RM booking
			today = datetime.datetime.today().date()
			if today == booking_date:
				raise CannotAllowBooking('same_day_mail_in', ticket)

			# check for post-8pm booking for the following day
			now = datetime.datetime.now()
			cutoff = 19
			date_diff = date - now.date()
			if now.hour > cutoff and date_diff.days == 1:  # after 8pm, booking date is tomorrow
				raise CannotAllowBooking('booking_is_tomorrow', ticket)

			# check whether collection is booked for the afternoon
			if booking_date.hour > 13:  # booking date is after 1pm
				raise CannotAllowBooking('collection_in_afternoon', ticket)

		# all checks have passed - send a confirmation email
		macro_id = 23336093706001
		r = zendesk.client.tickets.show_macro_effect(ticket, macro_id)
		zendesk.client.tickets.update(r.ticket)

		return True

	booking_item = monday.items.misc.WebBookingItem(web_booking_item_id).load_from_api()

	try:
		order_id = booking_item.woo_commerce_order_id.value
		main = monday.items.MainItem()

		# extract Woo Commerce order data
		woo_order_data = woocommerce.woo.get(f"orders/{order_id}")

		if woo_order_data.status_code != 200:
			notify_admins_of_error(
				f"Could not find order {order_id} in Woo Commerce\n\n{woo_order_data.text}")
			raise WebBookingTransferError(
				f"Could not find order {order_id} in Woo Commerce")

		woo_order_data = woo_order_data.json()

		# try:
		# 	booking_item.add_update(json.dumps(woo_order_data, indent=4))
		# except Exception as e:
		# 	notify_admins_of_error(f"Could not Dump Order details to Wb Booking Item ({str(booking_item)})\n\n\{str(e)}")

		name = woo_order_data['billing']['first_name']
		email = woo_order_data['billing']['email']
		phone = woo_order_data['billing']['phone']
		try:
			booking_date = [_ for _ in woo_order_data['meta_data'] if _['key'] == 'booking_time'][0]['value']
			booking_date = parse(booking_date)
		except IndexError:
			booking_date = None

		try:
			point_of_collection = [_ for _ in woo_order_data['meta_data'] if _['key'] == 'point_of_collection'][0]['value']
		except IndexError:
			point_of_collection = None

		address_notes = woo_order_data['billing']['address_1']
		address_street = woo_order_data['billing']['address_2']
		address_postcode = woo_order_data['billing']['postcode']
		payment_method = woo_order_data['payment_method_title']

		if 'cash' in payment_method.lower():
			payment_method = 'Cash'
		elif 'stripe' in payment_method.lower():
			payment_method = 'Stripe Payment'
		elif 'paypal' in payment_method.lower():
			payment_method = 'Paypal Payment'
		else:
			payment_method = 'Other'

		if woo_order_data['transaction_id']:
			payment_status = 'Confirmed'
		else:
			if 'cash' in payment_method.lower():
				payment_status = 'Pay In Store - Pending'
			else:
				payment_status = 'Unsuccessful'

		woo_commerce_product_ids = [str(line['product_id']) for line in woo_order_data['line_items']]
		woo_commerce_product_data = woocommerce.woo.get(
			f"products/",
			params={
				'include': ','.join(woo_commerce_product_ids)
			}
		)

		if woo_commerce_product_data.status_code != 200:
			notify_admins_of_error(
				f"{order_id} failed to retrieve anything from Woo Commerce: {woo_commerce_product_data.text}"
			)
			raise WebBookingTransferError(
				f"{order_id} failed to retrieve anything from Woo Commerce: {woo_commerce_product_data.text}"
			)

		if len(woo_commerce_product_ids) != len(woo_commerce_product_data.json()):
			log.warning = f"Could not find all products in {order_id} in Woo Commerce"
			notify_admins_of_error(
				f"Could not find all products in {order_id} in Woo Commerce"
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
				f"Could not find a service product: {woo_commerce_product_data}"
			)
			service = 'Unconfirmed'
		elif 'national courier' in service_products[0]['name'].lower():
			service = 'Mail-In'
		elif 'london courier' in service_products[0]['name'].lower():
			service = 'Stuart Courier'
		elif 'walk' in service_products[0]['name'].lower():
			service = 'Walk-In'
		else:
			raise WebBookingTransferError(f'{str(order_id)} could not determine service type')

		main.service = service
		booking_item.service = service

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
					log.error(f"Could not find Woo product in Eric: {str(_['name'])}({str(_['id'])})")

		except Exception as e:
			notify_admins_of_error(f"Could Not Fetch Products for Web Booking: {e}")

		if len(search_results) != len(repair_products):
			notify_admins_of_error(
				f"Could not find all products in {order_id} in Eric")

		products = search_results
		main.products_connect = [str(_.id) for _ in products]

		repair_type = 'Repair'
		for p in products:
			if 'diagnostic' in p.name.lower():
				repair_type = 'Diagnostic'
				break

		main.repair_type = repair_type
		booking_item.repair_type = repair_type

		device_ids = [p.device_id for p in products if p.device_id is not None]
		device_id = device_ids[0] if device_ids else None
		if device_id:
			d_id = device_id
			device_data = app.services.monday.api.client.get_api_items([d_id])[0]
			device = monday.items.DeviceItem(device_data['id'], device_data)
			email_subject = f"Your {device.name} Repair"
		else:
			device_id = 4028854241  # Other Device
			device = monday.items.DeviceItem(4028854241)
			email_subject = "Your Repair with iCorrect"

		main.device_id = int(device_id)

		# create zendesk ticket
		user_search = zendesk.helpers.search_zendesk(str(woo_order_data['billing']['email']))
		if not user_search:
			# no user found, create user
			log.debug(f"No User Found, creating")
			try:
				user = zendesk.helpers.create_user(
					name,
					email,
					phone,
				)
			except APIException as e:
				log.debug(f"Could not create user: {e}")
				notify_admins_of_error("Could not create user: " + str(e))
				raise WebBookingTransferError(f"Could not create user: {e}")

		elif len(user_search) == 1:
			user = next(user_search)
		else:
			raise WebBookingTransferError(f"Multiple users found ({len(search_results)}) for {email}")

		booking_text = f"Website Notes:\n" + woo_order_data['customer_note']

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

		main.email = email
		booking_item.email = email
		main.phone = phone
		booking_item.phone = phone
		main.ticket_id = str(ticket.id)
		booking_item.ticket_id = str(ticket.id)
		main.ticket_url = [
			str(ticket.id),
			f"https://icorrect.zendesk.com/agent/tickets/{ticket.id}",
		]
		desc = f"{device.name}\n\n"
		for p in products:
			d_name = p.name.replace(device.name, '')
			desc += f"{d_name} - £{int(p.price.value)}\n"
		booking_item.description = desc
		main.description = desc

		if point_of_collection:
			main.point_of_collection = point_of_collection
			booking_item.point_of_collection = point_of_collection
		if address_notes:
			main.address_notes = address_notes
			booking_item.address_notes = address_notes
		if address_street:
			main.address_street = address_street
			booking_item.address_street = address_street
		if address_postcode:
			main.address_postcode = address_postcode
			booking_item.address_postcode = address_postcode
		if booking_date:
			main.booking_date = booking_date
			booking_item.booking_date = booking_date
		if payment_status:
			main.payment_status = payment_status
			booking_item.pay_status = payment_status
		if payment_method:
			main.payment_method = payment_method
			booking_item.pay_method = payment_method

		main.client = 'End User'
		booking_item.client = 'End User'
		main.main_status = 'Awaiting Confirmation'
		main.notifications_status = 'ON'

		main.create(name)

		if woo_commerce_product_data:
			booking_text += "\n\nWebsite Products:\n\n"
			for wp in woo_commerce_product_data:
				try:
					price = int(float(wp['price']))
				except Exception as e:
					price = "Could not fetch price from WooCommerce"
					notify_admins_of_error(f"Could not fetch price from WooCommerce: {e}")
				booking_text += f"{wp['name']}: £{price}\n"

		booking_item.booking_notes = booking_text

		main.add_update(booking_text, main.notes_thread_id.value)
		main.add_update(main.get_stock_check_string([str(p.id) for p in products]), main.notes_thread_id.value)

		sync_to_zendesk(main.id, ticket.id)

		send_confirmation_email()

		booking_item.transfer_status = 'Complete'
		booking_item.email = email
		booking_item.main_item_id = str(main.id)
	except Exception as e:
		log.error(e)
		notify_admins_of_error(f"Error transferring web booking: {e}")
		booking_item.transfer_status = 'Error'
		raise e

	booking_item.commit()

	monday.api.monday_connection.items.change_multiple_column_values(
		main.BOARD_ID,
		main.id,
		{
			"device0": {"labels": [str(device.name)]}
		},
		create_labels_if_missing=True
	)

	return booking_item


def push_web_enquiry_to_zendesk(web_enquiry_id):
	try:
		enquiry = monday.items.misc.WebEnquiryItem(web_enquiry_id)
		device = enquiry.device_type_string.value

		if device:
			if 'macbook' in device.lower():
				device = 'MacBook'
			elif 'iphone' in device.lower():
				device = 'iPhone'
			elif 'watch' in device.lower():
				device = 'Apple Watch'
			elif 'ipad' in device.lower():
				device = 'iPad'
			elif 'ipod' in device.lower():
				device = 'iPod'

		if not device:
			subject = 'Your Enquiry with iCorrect'
			device_name = 'No Device Selected'
		else:
			subject = f"Your {device} Enquiry with iCorrect"
			device_name = device.capitalize()

		model = enquiry.model_string.value

		if not model:
			model = "No Model Selected"
		else:
			model = model.capitalize()

		search_results = zendesk.helpers.search_zendesk(str(enquiry.email.value))
		if not search_results:
			if enquiry.phone.value:
				user = zendesk.client.users.create(
					User(
						name=str(enquiry.name).capitalize(),
						email=str(enquiry.email.value),
						phone=int(enquiry.phone.value)
					)
				)
			else:
				user = zendesk.client.users.create(
					User(
						name=str(enquiry.name).capitalize(),
						email=str(enquiry.email.value)
					)
				)
		else:
			user = next(search_results)

		body = f"""	Device: {device_name}
					Model: {model}

					Enquiry: {enquiry.body.value}
		"""

		ticket = Ticket(
			description=subject,
			requester_id=str(user.id),
			comment=Comment(
				public=False,
				body=body
			),
			tags=['web_enquiry']
		)

		ticket = zendesk.client.tickets.create(ticket).ticket
		enquiry.zendesk_id = str(ticket.id)
		enquiry.commit()

		# generate initial AI response
		ai_thread = openai.utils.create_thread()

		ai_body = f"""name: {user.name},
		email: {user.email},
		phone: {user.phone},
		device: {device_name},
		enquiry: {enquiry.body.value}
		"""

		openai.utils.add_message_to_thread(ai_thread.id, ai_body)

		run = openai.utils.run_thread(ai_thread.id, conf.OPEN_AI_ASSISTANTS['enquiry'])

		# wait for run to finish
		comment = None
		while comment is None:
			if run.status in ('queued', 'in_progress'):
				time.sleep(2)
				run = openai.utils.fetch_run(ai_thread.id, run.id)
			elif run.status == 'completed':
				comment = openai.utils.client.beta.threads.messages.list(ai_thread.id, limit=1).data[0].content[
					0].text.value
			elif run.status in ('requires_action', 'cancelling', 'cancelled', 'failed', 'expired'):
				comment = (f"Could not fetch AI response, run has invalid status: {run.status}\n\n"
						   f"run_id: {run.id}\nthread_id: {ai_thread.id}")
			else:
				raise RuntimeError(f"Unexpected run status: {run.status}")
		try:
			assistant_name = openai.utils.get_assistant_data(str(run.assistant_id))['name']
		except KeyError:
			assistant_name = 'Unregistered assistant'

		comment = f"!!!AI-NOTE!! (assistant: {assistant_name})\n\n{comment}"

		ticket.comment = Comment(
			body=comment,
			public=False
		)
		ticket.tags.extend(['ai_handled'])
		zendesk.client.tickets.update(ticket)

	except Exception as e:
		notify_admins_of_error(e)
		raise e


class WebBookingTransferError(EricError):
	pass
