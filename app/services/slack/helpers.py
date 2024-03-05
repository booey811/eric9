import uuid
import hashlib

from ...services import monday, zendesk


def extract_meta_from_main_item(main_item=None, main_id=''):
	user = device = products = custom_lines = None

	if not main_item and not main_id:
		raise ValueError("No main item or main id provided")

	if not main_item and main_id:
		main_item = monday.items.MainItem(main_id)

	if main_item.ticket_id.value:
		ticket = zendesk.client.tickets(id=main_item.ticket_id.value)
		user = ticket.requester

	if main_item.device_id:
		device = monday.items.DeviceItem(main_item.device_id)

	if main_item.products:
		products = main_item.products

	if main_item.custom_quote_connect.value:
		custom_lines = [monday.items.misc.CustomQuoteLineItem(line_id) for line_id in
						main_item.custom_quote_connect.value]

	imei_sn = pay_status = None
	if main_item.imeisn.value:
		imei_sn = main_item.imeisn.value

	if main_item.payment_status.value:
		pay_status = main_item.payment_status.value

	return create_meta(
		user=user, device=device, products=products, main_item=main_item, custom_lines=custom_lines,
		imei_sn=imei_sn, pay_status=pay_status
	)


def create_meta(
		user_id=None, device_id=None, product_ids=None, user=None, device=None,
		products=None, main_item=None, custom_lines=None, imei_sn=None, pay_status=None
):
	meta = {
		'main_id': '',
		'user': {
			'name': '',
			'id': '',
			'email': '',
			'phone': ''
		},
		'device_id': '',
		'product_ids': [],
		'custom_products': [],
		'pre_checks': [],
		'additional_notes': '',
		'imei_sn': '',
		'pay_status': '',
		'pc': '',
	}

	if not user and not user_id:
		pass
	elif not user and user_id:
		user = zendesk.client.users(id=user_id)

	if user:
		meta['user']['name'] = user.name
		meta['user']['id'] = user.id
		meta['user']['email'] = user.email
		meta['user']['phone'] = user.phone

	if not device and not device_id:
		pass
	elif not device and device_id:
		device = monday.items.DeviceItem(device_id)

	if device:
		meta['device_id'] = str(device.id)

	if not products and not product_ids:
		pass
	elif product_ids and not products:
		products = monday.items.ProductItem.get(product_ids)

	if products:
		meta['product_ids'] = [str(p.id) for p in products]

	if main_item:
		meta['main_id'] = str(main_item.id)

	if custom_lines:
		meta['custom_products'] = [line.prepare_cache_data() for line in custom_lines]

	if imei_sn:
		meta['imei_sn'] = imei_sn

	if pay_status:
		meta['pay_status'] = pay_status

	return meta


def generate_unique_block_id():
	# Generate a UUID
	unique_id = uuid.uuid4()

	# Create a hash of the UUID
	hash_object = hashlib.sha1(str(unique_id).encode())
	hex_dig = hash_object.hexdigest()

	# Take the first 10 characters of the hash for a short block_id
	short_id = hex_dig[:10]

	return short_id
