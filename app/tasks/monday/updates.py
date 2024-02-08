import logging
from moncli.api_v2.exceptions import MondayApiError

from ...models import MainModel
from ...utilities import notify_admins_of_error

log = logging.getLogger('eric')


def add_message_to_update_thread(update_thread_id, update, title='', main_id=None, main_item=None):
	if not main_item and not main_id:
		raise RuntimeError('Must provide Item ID or Item Object')
	elif main_item and main_id:
		raise RuntimeError('Must provide Item ID or Item Object, not both')
	elif main_id:
		main_item = MainModel(main_id)
	else:
		raise RuntimeError('Must provide Item ID or Item Object')

	if title:
		message = f"{title}\n\n{update}"
	else:
		message = update

	try:
		updates = main_item.model.item.get_updates()
		log.debug("Updates: " + str(updates))
		for u in updates:
			print(f"Update ID: {u['id']} comparing with desired ID: {update_thread_id}")
		update = [u for u in updates if str(u['id']) == str(update_thread_id)][0]
	except IndexError:
		raise RuntimeError(f"Update Thread ID {update_thread_id} not found in MainItem({main_item.model.id})")
	try:
		update.add_reply(message)
	except MondayApiError as e:
		log.error(f"Error adding message to update thread({str(main_item)}): {e}")
		notify_admins_of_error(f"Error adding message to update thread({str(main_item)}): {e}")
		message = message.replace('"', '').replace("/", '').replace('-', '')
		update.add_reply(message)
	return False
