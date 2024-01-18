import os

import app

import config

env = os.getenv('ENV', 'testing')
port = int(os.environ.get('PORT', 8000))  # Default to 8000 for local development
conf = config.get_config(env)
if env != 'production':
	for v in conf().get_vars():
		print(v)

eric = app.create_app(env)


if __name__ == '__main__':
	if env == 'production':
		pass
	elif env == 'testing':
		pass
	elif env == 'development':
		from app.tasks import scheduling
		from app.utilities import users
		from app.services import monday
		from app.models import MainModel

		user = users.User('gabe')

		# repairs = monday.get_group_items(conf.MONDAY_MAIN_BOARD_ID, conf.TEST_PROOF_ITEMS)
		# repairs = [MainModel(r.id, r) for r in repairs]
		# scheduling.sync_schedule(user, "new_group26478")

	else:
		raise Exception(f"Invalid ENV: {env}")
