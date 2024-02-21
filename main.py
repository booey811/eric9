import logging
import os

import app

log = logging.getLogger('eric')

env = os.getenv('ENV', 'development')
port = int(os.environ.get('PORT', 8000))  # Default to 8000 for local development

eric = app.create_app()


if __name__ == '__main__':
	if env == 'production':
		eric.run()
	elif env == 'testing':
		eric.run()
	elif env == 'development':
		from app.tasks.sync_platform import sync_to_zendesk
		from app.tasks.monday import sessions
		w_id = 6017161322
		i_id = 6099674053
		t_id = 25625

		phase_model_id = 6106627585

		import datetime
		from app.tasks.monday.web_bookings import transfer_web_booking
		# notifications.notify_zendesk.send_macro(i_id)
		from app.services import zendesk

	else:
		raise Exception(f"Invalid ENV: {env}")
