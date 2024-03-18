import logging

from ...services import monday, woocommerce
from ...utilities import users, notify_admins_of_error

log = logging.getLogger('eric')


def create_profit_models_from_products_board():
	"""
	Iterates through all products on the products board with Profit Model Gen Text == 'n' and creates a repair profit
	model for each product, setting the search column to 'y' when successful.
	"""

	search = monday.items.ProductItem(search=True)
	res = search.search_board_for_items('profit_model_gen_text', 'n')
	#
	prods = [monday.items.ProductItem(prod['id'], prod) for prod in res]
	failed = []
	while prods:
		for prod in prods:
			try:
				r_model = monday.items.misc.RepairProfitModelItem()
				r_model.products_connect = [str(prod.id)]
				r_model.parts_connect = [str(_) for _ in prod.parts_connect.value]
				r_model.commit(name=prod.name)
				prod.profit_model_gen_text = 'y'
				prod.commit()
				log.debug(f"Created repair model for {str(prod)}")
			except Exception as e:
				log.error(f"Failed to create repair model for {str(prod)}: {e}")
				failed.append(prod.id)

			res = search.search_board_for_items('profit_model_gen_text', 'n')
			prods = [monday.items.ProductItem(prod['id'], prod) for prod in res]

	if failed:
		print("FAILURES")
		print(failed)

	return failed


def adjust_web_price(product_id, new_price, old_price=None, user_id=None):
	if not old_price:
		old_price_text = 'Not Given'
	else:
		old_price_text = str(old_price)
	try:
		prod = monday.items.ProductItem(product_id).load_from_api()
		try:
			if not user_id:
				user_name = 'Unknown User'
			else:
				user = users.User(monday_id=user_id)
				user_name = user.name

			woo_id = prod.woo_commerce_product_id.value

			if not woo_id:
				raise ValueError

			woocommerce.adjust_price(
				woo_id,
				new_price
			)
			update = f"Price Changed by '{user_name}' ({old_price_text} -> {new_price})"
			status = 'Synced'

		except ValueError:
			update = f"Could Not Update Price: No Woo Commerce ID found (revert to previous price: {old_price_text})"
			if old_price:
				prod.price = int(old_price)
			status = 'Error'
		except Exception as e:
			update = f"Could Not Update Price: Unknown Error\n\n{str(e)}\n\n(revert to previous price: {old_price_text})"
			if old_price:
				prod.web_price = int(old_price)
			status = 'Error'

		prod.price_sync_status = status
		prod.commit()
		prod.add_update(
			update
		)
	except Exception as e:
		notify_admins_of_error(f"Could Not Update Web Price\n\n{str(e)}")
		raise e
