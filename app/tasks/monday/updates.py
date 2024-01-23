from app.models import MainModel


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
		update = [u for u in main_item.model.item.get_updates() if u['id'] == update_thread_id][0]
	except IndexError:
		raise RuntimeError(f"Update Thread ID {update_thread_id} not found in MainItem({main_item.model.id})")

	update.add_reply(message)

	return False
