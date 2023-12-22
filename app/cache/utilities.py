from . import get_redis_connection
from ..services import monday
from ..models import ProductModel


def build_product_cache(environment):
	if environment == 'development':
		products_board = monday.client.get_board(2477699024)
		air_3 = products_board.get_group('ipad_air_3')
		iphone_13_pro = products_board.get_group('iphone_13_pro')
		items = air_3.get_items(get_column_values=True) + iphone_13_pro.get_items(get_column_values=True)
		prods = [ProductModel(item.id, item) for item in items]
		for prod in prods:
			prod.save_to_cache()
		print()