from ... import monday
from . import objects


def generate_device_options_list(filter_by_name=''):
	devices = monday.items.DeviceItem.fetch_all()

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

	options = {
		"option_groups": objects.generate_option_groups(raw_dict)
	}

	return options


def generate_product_options(device_id=None, filter_by_name=''):
	products = monday.items.ProductItem.fetch_all()

	if device_id:
		products = [_ for _ in products if str(_.device_id) == str(device_id)]

	if filter_by_name:
		products = [_ for _ in products if filter_by_name.lower() in _.name.lower()]

	options = {
		"options": [{"text": _.name, "value": str(_.id)} for _ in products]
	}

	return options
