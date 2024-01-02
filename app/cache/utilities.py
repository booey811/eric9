import logging

from . import get_redis_connection
from ..services import monday
from ..models import ProductModel
from app.models import get_products

log = logging.getLogger()


def build_product_cache(environment):
	def items_in_batch(mon_items, batch_size=100):
		for i in range(0, len(mon_items), batch_size):
			yield mon_items[i:i + batch_size]

	if environment == 'development':
		products_board = monday.client.get_board(2477699024)
		air_3 = products_board.get_group('ipad_air_3')
		iphone_13_pro = products_board.get_group('iphone_13_pro')
		items = air_3.get_items(get_column_values=True) + iphone_13_pro.get_items(get_column_values=True)
		prods = [ProductModel(item.id, item) for item in items]
		for prod in prods:
			prod.save_to_cache()
		print()
	elif environment == 'production':
		print(f"Building Product Cache: {environment}")
		prod_board = monday.client.get_board_by_id(2477699024)
		raw_items = prod_board.get_items()
		print(f"Fetched {len(raw_items)} monday items")
		all_items = items_in_batch([_.id for _ in raw_items])
		while all_items:
			try:
				ids = next(all_items)
				print(f"Processing Block of {len(ids)}")
				fetch = monday.client.get_items(ids=ids, get_column_values=True)
				for item in fetch:
					product = ProductModel(item.id, item)
					product.save_to_cache()
			except StopIteration:
				print("Complete")



