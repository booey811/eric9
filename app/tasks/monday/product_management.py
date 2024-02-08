import logging

from app.services import monday
from app.models import DeviceModel

log = logging.getLogger('eric')


def check_devices_linked_to_products():
	"""cycles through devices on the devices board, checking for missing Product Group IDs"""
	log.debug('Updating Devices')
	d_board = monday.conn.get_boards(ids=[3923707691])[0]
	log.debug("Got Devices")

	_s = d_board.get_items(get_column_values=True)
	devices = [DeviceModel(i.id, i) for i in _s]

	p_board = monday.conn.get_boards(ids=[2477699024])[0]

	for d in devices:
		d.connect_to_product_group()
		# log.debug(f"Checking {d.model.name}")
		#
		# if not d.model.legacy_eric_device_id or d.model.legacy_eric_device_id == "new_group77067":  # index group ID
		#
		# 	if d.products:
		# 		prod = d.products[0]
		# 		device_group_id = prod.model.item.get_group().id
		# 		if device_group_id == "new_group77067":  # index Group ID
		# 			prod = d.products[1]
		# 			device_group_id = prod.model.item.get_group().id
		# 		d.model.legacy_eric_device_id = device_group_id
		# 		d.model.save()
		#
		# 	elif not d.model.product_index_connect:
		#
		# 		log.debug(f"No legacy Eric ID available, creating")
		# 		group = p_board.add_group(group_name=d.model.name)
		# 		d.model.legacy_eric_device_id = group.id
		# 		d.model.save()
		# 		log.debug(group.id)
		#
		# 	else:
		# 		raise Exception('Unable to auto-index new Device item')
