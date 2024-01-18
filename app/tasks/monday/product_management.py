import logging

from app.services import monday
from app.models import DeviceModel

log = logging.getLogger('eric')


def check_devices_linked_to_products():
	"""cycles through devices on the devices board, checking for missing Product Group IDs"""
	log.debug('Updating Devices')
	d_board = monday.client.get_boards(ids=[3923707691])[0]
	log.debug("Got Devices")

	_s = d_board.get_items(get_column_values=True)
	devices = [DeviceModel(i.id, i) for i in _s]

	p_board = monday.client.get_boards(ids=[2477699024])[0]

	for d in devices:
		log.debug(f"Checking {d.model.name}")
		if not d.model.legacy_eric_device_id:
			log.debug(f"No legacy Eric ID available, creating")
			group = p_board.add_group(group_name=d.model.name)
			d.model.legacy_eric_device_id = group.id
			d.model.save()
			log.debug(group.id)
