import os

import app

import asyncio
from app import create_app
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler

env = os.getenv('ENV', 'development')
eric = app.create_app(env)
slack_app = AsyncApp(token=os.environ['SLACK-DEV-APP'])  # Initialize with your token


async def run_quart():
	await eric.run_task(port=5000)


async def run_slack():
	handler = AsyncSocketModeHandler(slack_app, os.environ['SLACK-DEV-APP'])  # Initialize with your token
	await handler.start_async()


async def main():
	await asyncio.gather(run_quart(), run_slack())


def print_routes():
	for rule in eric.url_map.iter_rules():
		methods = ", ".join(rule.methods)
		print(f"{rule.endpoint} {methods} {rule.rule}")


if __name__ == '__main__':
	if env == 'production':
		asyncio.run(main())

	elif env == 'development':
		asyncio.run(main())




	# products_board = monday.client.get_board(2477699024)
	# air_3 = products_board.get_group('ipad_air_3')
	# iphone_13_pro = products_board.get_group('iphone_13_pro')
	# items = air_3.get_items(get_column_values=True) + iphone_13_pro.get_items(get_column_values=True)
	# prods = [ProductModel(item.id, item) for item in items]
	else:
		raise Exception(f"Invalid ENV: {env}")
