from ...services import monday, zendesk


def extract_meta_from_main_item(main_item=None, main_id=''):
	user = device = products = None

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

	return create_meta(user=user, device=device, products=products, main_item=main_item)


def create_meta(user_id=None, device_id=None, product_ids=None, user=None, device=None, products=None, main_item=None):
	meta = {
		'main_item': {},
		'user': {
			'name': '',
			'id': '',
			'email': '',
			'phone': ''
		},
		'device': {},
		'products': []
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
		meta['device'] = device.prepare_cache_data()

	if not products and not product_ids:
		pass
	elif product_ids and not products:
		products = monday.items.ProductItem.get(product_ids)

	if products:
		for product in products:
			meta['products'].append(product.prepare_cache_data())

	if main_item:
		meta['main_item'] = main_item._api_data

	return meta
