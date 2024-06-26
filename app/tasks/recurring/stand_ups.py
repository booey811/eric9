import datetime

import pytz

import config
from app.utilities import users
from app.services.slack import blocks, slack_app, flows
from app.cache import get_redis_connection
from app.cache.rq import q_high

conf = config.get_config()


def generate_daily_stand_up_views(user_names=('safan', 'andres', 'ferrari')):
	# clear the current cache first
	redis = get_redis_connection()
	for key in redis.scan_iter("stand_up:*"):
		redis.delete(key)

	if not isinstance(user_names, (list, tuple)):
		raise Exception(f"Expected a list or tuple of user names, got {type(user_names)}")

	enqueue_at = datetime.datetime.now(tz=pytz.timezone('Europe/London')).replace(
		hour=9,
		minute=0,
		second=0,
		microsecond=0
	)
	enqueue_at = enqueue_at.astimezone(pytz.utc)

	users_to_request = [users.User(name=n) for n in user_names]
	flow = flows.StandUpFlow(None, None, None)
	for user in users_to_request:
		flow.generate_stand_up_view(user)

	if conf.CONFIG == 'PRODUCTION':
		q_high.enqueue_at(
			datetime=enqueue_at,
			f=request_daily_stand_ups,
		)
	else:
		request_daily_stand_ups(user_names=user_names)

	return user_names


def request_daily_stand_ups(user_names=('safan', 'andres', 'ferrari'), date=datetime.datetime.now().date()):
	if not isinstance(user_names, (list, tuple)):
		raise Exception(f"Expected a list or tuple of user names, got {type(user_names)}")

	users_to_request = [users.User(name=n) for n in user_names]
	# date in strformat: Sun 8th Nov
	formatted_date = date.strftime("%a %d %b")

	for user in users_to_request:
		message_blocks = []
		message_blocks.append(blocks.add.header_block(f"Daily Stand Up: {formatted_date}"))
		message_blocks.append(blocks.add.actions_block(
			block_elements=[
				blocks.add.elements.button_element(
					button_text="Submit Stand Up",
					button_value=f"stand_up:{user.name}",
					action_id="begin_stand_up"
				)
			],
		))
		slack_app.client.chat_postMessage(
			channel=user.slack_id,
			blocks=message_blocks,
			text='Daily Stand Up!'
		)

	return user_names
