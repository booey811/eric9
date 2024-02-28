import logging

from ...services import monday

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
