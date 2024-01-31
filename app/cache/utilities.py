import logging

from . import get_redis_connection
from ..services import monday
from ..models import ProductModel, DeviceModel

log = logging.getLogger('eric')


def build_product_cache():
	log.info(f'Building product cache')
	products_board = monday.client.get_board(2477699024)
	all_simple_items = products_board.get_items()
	log.info(f"Fetched {len(all_simple_items)} items (simple)")
	block_size = 25
	pipe = get_redis_connection().pipeline()
	# Cycle through the long list
	for i in range(0, len(all_simple_items), block_size):
		# Create a block (slice) for this iteration
		log.debug(f"Fetching block {i // block_size + 1} of {len(all_simple_items) // block_size + 1}")
		block = all_simple_items[i:i + block_size]
		items = monday.get_items([_.id for _ in block], column_values=True)
		log.info(f"Fetched {len(items)} items fully")
		for item in items:
			p = ProductModel(item.id, item)
			log.debug(str(p))
			p.model
			p.save_to_cache(pipe)
	pipe.execute()
	log.info(f"Product cache built")


def build_device_cache():
	log.info("Building Device Cache")
	devices_board = monday.client.get_board(3923707691)  # Devices Board
	all_simple_items = devices_board.get_items()
	log.info(f"Fetched {len(all_simple_items)} items (simple)")
	block_size = 25
	pipe = get_redis_connection().pipeline()
	# Cycle through the long list
	for i in range(0, len(all_simple_items), block_size):
		# Create a block (slice) for this iteration
		log.debug(f"Fetching block {i // block_size + 1} of {len(all_simple_items) // block_size + 1}")
		block = all_simple_items[i:i + block_size]
		items = monday.get_items([_.id for _ in block], column_values=True)
		log.info(f"Fetched {len(items)} items fully")
		for item in items:
			d = DeviceModel(item.id, item)
			model = d.model
			log.debug(str(d))
			d.save_to_cache(pipe)
	pipe.execute()