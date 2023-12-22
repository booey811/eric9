import os

import app

import asyncio
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler

env = os.getenv('ENV', 'development')
port = int(os.environ.get('PORT', 8000))  # Default to 8000 for local development

eric = app.create_app(env)
slack_app = AsyncApp(token=os.environ['SLACK_APP'])  # Initialize with your token


async def run_quart():
	await eric.run_task(port)


async def run_slack():
	handler = AsyncSocketModeHandler(slack_app, os.environ["SLACK_APP"])  # Initialize with your token
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

	else:
		raise Exception(f"Invalid ENV: {env}")
