from ... import monday
from . import objects


def generate_device_options_list(filter_by_name=''):
	devices = monday.items.DeviceItem.fetch_all(slack_data=False)

	if filter_by_name:
		devices = [device for device in devices if filter_by_name.lower() in device.name.lower()]

	device_types = set([device.device_type.value for device in devices])
	raw_dict = {
		dt: [] for dt in device_types
	}

	for device in devices:
		d_type = device.device_type.value
		if not d_type:
			d_type = 'Device'
		raw_dict[d_type].append([device.name, device.id])

	for d_set in raw_dict:
		raw_dict[d_set].sort(key=lambda x: x[0])
		raw_dict[d_set].reverse()

	return objects.generate_option_groups(raw_dict)


def generate_product_options(device_id=None, filter_by_name=''):
	products = monday.items.ProductItem.fetch_all()

	if device_id:
		products = [_ for _ in products if str(_.device_id) == str(device_id)]

	if filter_by_name:
		products = [_ for _ in products if filter_by_name.lower() in _.name.lower()]

	return [objects.plain_text_object(_.name, _.id) for _ in products]


def create_slack_friendly_parts_options(search_string):
	search_terms = search_string.split(' ')
	all_parts = monday.items.PartItem.fetch_all()
	part_options = []
	for part in all_parts:
		if 'index' in part.name.lower():
			continue
		if all(term.lower() in part.name.lower() for term in search_terms):
			part_options.append(objects.plain_text_object(part.name, str(part.id)))
		if len(part_options) > 98:
			break
	part_options.sort(key=lambda x: x['text']['text'].lower(), reverse=True)
	return part_options