import logging
import json

from ...cache import get_redis_connection
from ...services.slack import slack_app, flows, builders
from ...utilities import notify_admins_of_error, users

log = logging.getLogger('eric')


@slack_app.command('/error')
def show_metadata_retrieval_menu(ack, client, body):
	log.info('showing metadata retrieval menu')
	flow_controller = flows.MiscellaneousFlow(slack_client=client, ack=ack, body=body, meta={})
	flow_controller.metadata_retrieval_menu()


@slack_app.action("revive_metadata")
def revive_metadata_view(ack, client, body):
	log.info('reviving metadata view')

	meta_key = body['actions'][0]['value']
	meta = get_redis_connection().get(meta_key).decode('utf-8')
	try:
		meta = json.loads(meta)
	except json.JSONDecodeError as e:
		client.views_update(
			view_id=body['view']['id'],
			view=builders.ResultScreenViews().get_error_screen(
				f"An error occurred while getting your metadata\n\n{e}\n\n{meta}")
		)
		notify_admins_of_error(e)
		return

	if meta.get('flow') == 'walk_in':
		flow_controller = flows.WalkInFlow(slack_client=client, ack=ack, body=body, meta=meta)
		flow_controller.show_repair_details('update', body['view']['id'])
		return
	else:
		client.views_update(
			view_id=body['view']['id'],
			view=builders.ResultScreenViews().get_error_screen(
				f"Could not revive your metadata, but it's all down here\n\n{meta}")
		)
		return


@slack_app.event("app_home_opened")
def render_home_screen(client, ack, body):
	log.info('rendering home screen')
	flow = flows.HomeScreenFlow(slack_client=client, ack=ack, body=body)
	flow.show_home_screen()
	return


@slack_app.action('begin_stand_up')
def show_standup_selection_menu(ack, client, body):
	log.info('Opening Stand Up')
	flow = flows.StandUpFlow(slack_client=client, ack=ack, body=body)
	user = users.User(slack_id=body['user']['id'])
	flow.get_stand_up_view(user)
	return
