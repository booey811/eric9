import logging

from . import get_redis_connection
from ..services import monday
from ..models import ProductModel

log = logging.getLogger('eric')


def build_product_cache(environment):
	log.info(f'Building product cache with environment={environment}')
	products_board = monday.client.get_board(2477699024)
	if environment == 'development':
		products_board.get_items(limit=100)
		air_3 = products_board.get_group('ipad_air_3')
		iphone_13_pro = products_board.get_group('iphone_13_pro')
		items = air_3.get_items(get_column_values=True) + iphone_13_pro.get_items(get_column_values=True)
		prods = [ProductModel(item.id, item) for item in items]
		for prod in prods:
			# pass pipeline in here, and use it as conditional in save_to_cache
			prod.save_to_cache()
		# then execute pipe
		print()
	if environment == 'production':
		all_simple_items = products_board.get_items()
		log.info(f"Fetched {len(all_simple_items)} items (simple)")
		block_size = 25
		# Cycle through the long list
		for i in range(0, len(all_simple_items), block_size):
			# Create a block (slice) for this iteration
			block = all_simple_items[i:i + block_size]
			items = monday.get_items([_.id for _ in block], column_values=True)
			log.info(f"Fetched {len(items)} items fully")
			for item in items:
				p = ProductModel(item.id, item)
				log.debug(str(p))
				p.model
				p.save_to_cache()

