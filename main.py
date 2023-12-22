import os

import app

env = os.getenv('ENV', 'development')
eric = app.create_app(env)

if __name__ == '__main__':
	if env == 'production':
		eric.run()

	if env == 'development':
		from app.services import monday
		from app.models import ProductModel
		from app.models import DeviceModel
		# products_board = monday.client.get_board(2477699024)
		# air_3 = products_board.get_group('ipad_air_3')
		# iphone_13_pro = products_board.get_group('iphone_13_pro')
		# items = air_3.get_items(get_column_values=True) + iphone_13_pro.get_items(get_column_values=True)
		# prods = [ProductModel(item.id, item) for item in items]
	else:
		raise Exception(f"Invalid ENV: {env}")
