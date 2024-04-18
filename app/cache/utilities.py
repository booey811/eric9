import logging

from . import get_redis_connection
from ..services import monday

log = logging.getLogger('eric')


def clear_cache(key_prefix=''):
	log.info(f"Clearing cache for key: {key_prefix}")
	redis_connection = get_redis_connection()
	pipe = redis_connection.pipeline()
	for key in redis_connection.scan_iter(f"{key_prefix}*"):
		pipe.delete(key)
	pipe.execute()


def build_product_cache():
	def cache_item_set(item_set):
		for i in item_set:
			p = monday.items.ProductItem(i['id'], i)
			p.save_to_cache(pipe)

	log.info("Building product cache")
	clear_cache("product:*")
	pipe = get_redis_connection().pipeline()

	query_results = monday.api.monday_connection.boards.fetch_items_by_board_id(
		monday.items.ProductItem.BOARD_ID
	)['data']['boards'][0]['items_page']
	cursor = query_results['cursor']
	log.debug(f"Cursor: {cursor}, {len(query_results['items'])} items fetched")
	cache_item_set(query_results['items'])
	while cursor:
		query_results = monday.api.monday_connection.boards.fetch_items_by_board_id(
			monday.items.ProductItem.BOARD_ID,
			cursor=cursor
		)['data']['boards'][0]['items_page']
		cursor = query_results['cursor']
		log.debug(f"Cursor: {cursor}, {len(query_results['items'])} items fetched")
		cache_item_set(query_results['items'])
		if not cursor:
			break
	pipe.execute()


def build_device_cache():
	def cache_item_set(item_set):
		for i in item_set:
			d = monday.items.DeviceItem(i['id'], i)
			d.save_to_cache(pipe)

	log.info("Building Device Cache")
	clear_cache("device:*")
	pipe = get_redis_connection().pipeline()

	query_results = monday.api.monday_connection.boards.fetch_items_by_board_id(
		monday.items.DeviceItem.BOARD_ID
	)['data']['boards'][0]['items_page']
	cursor = query_results['cursor']
	log.debug(f"Cursor: {cursor}, {len(query_results['items'])} items fetched")
	cache_item_set(query_results['items'])
	while True:
		query_results = monday.api.monday_connection.boards.fetch_items_by_board_id(
			monday.items.DeviceItem.BOARD_ID,
			cursor=cursor
		)['data']['boards'][0]['items_page']
		cursor = query_results['cursor']
		log.debug(f"Cursor: {cursor}, {len(query_results['items'])} items fetched")
		cache_item_set(query_results['items'])
		if not cursor:
			break
	pipe.execute()


def build_part_cache():
	def cache_item_set(item_set):
		for i in item_set:
			p = monday.items.PartItem(i['id'], i)
			p.save_to_cache(pipe)

	log.info("Building Parts Cache")
	clear_cache("part:*")
	pipe = get_redis_connection().pipeline()

	query_results = monday.api.monday_connection.boards.fetch_items_by_board_id(
		monday.items.PartItem.BOARD_ID
	)['data']['boards'][0]['items_page']
	cursor = query_results['cursor']
	log.debug(f"Cursor: {cursor}, {len(query_results['items'])} items fetched")
	cache_item_set(query_results['items'])
	counter = len(query_results['items'])
	while True:
		query_results = monday.api.monday_connection.boards.fetch_items_by_board_id(
			monday.items.PartItem.BOARD_ID,
			cursor=cursor
		)['data']['boards'][0]['items_page']
		cursor = query_results['cursor']
		log.debug(f"Cursor: {cursor}, {len(query_results['items'])} items fetched")
		cache_item_set(query_results['items'])
		if not cursor:
			break
		counter += len(query_results['items'])
		log.debug(f"Total items fetched: {counter}")
	pipe.execute()


def build_pre_check_cache():
	def cache_item_set(item_set):
		for i in item_set:
			p = monday.items.misc.CheckItem(i['id'], i)
			p.save_to_cache(pipe)

	log.info("Building Pre-Check Item Cache")
	clear_cache("pre_check_item:*")
	pipe = get_redis_connection().pipeline()

	query_results = monday.api.monday_connection.boards.fetch_items_by_board_id(
		monday.items.misc.CheckItem.BOARD_ID
	)['data']['boards'][0]['items_page']
	cursor = query_results['cursor']
	log.debug(f"Cursor: {cursor}, {len(query_results['items'])} items fetched")
	cache_item_set(query_results['items'])
	counter = len(query_results['items'])
	while True:
		query_results = monday.api.monday_connection.boards.fetch_items_by_board_id(
			monday.items.misc.CheckItem.BOARD_ID,
			cursor=cursor
		)['data']['boards'][0]['items_page']
		cursor = query_results['cursor']
		log.debug(f"Cursor: {cursor}, {len(query_results['items'])} items fetched")
		cache_item_set(query_results['items'])
		if not cursor:
			break
		counter += len(query_results['items'])
		log.debug(f"Total items fetched: {counter}")
	pipe.execute()
