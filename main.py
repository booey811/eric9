import os

import app

import asyncio
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler

import config

env = os.getenv('ENV', 'testing')
port = int(os.environ.get('PORT', 8000))  # Default to 8000 for local development
conf = config.get_config(env)
if env != 'production':
	for v in conf().get_vars():
		print(v)
eric = app.create_app(env)
slack_app = AsyncApp(token=conf.SLACK_APP_TOKEN)  # Initialize with your token


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

	elif env == 'testing':
		asyncio.run(main())

	elif env == 'development':
		from app.services.slack import views

		# Example usage:
		builder = views.ModalViewBuilder("My Modal", "Submit", "Cancel", callback_id="my_modal")
		dropdown_block = views.blocks.create_dropdown_block("Select an option", "dropdown_action",
															[("Option 1", "option_1"), ("Option 2", "option_2")])
		multiselect_block = views.blocks.create_multiselect_block("Select multiple options", "multiselect_action",
																  [("Option A", "option_a"), ("Option B", "option_b")])

		builder.add_input_block(dropdown_block)
		builder.add_input_block(multiselect_block)

		modal_view_payload = builder.build_view_payload()

	else:
		raise Exception(f"Invalid ENV: {env}")
