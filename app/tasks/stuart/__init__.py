from ...services import monday, stuart


def book_collection(main_id):
	"""Book a collection for a main item"""
	main_item = monday.items.MainItem(main_id).load_from_api()
	try:
		job_data = stuart.helpers.generate_job_data(main_item, 'incoming')
	except Exception as e:
		main_item.add_update(f"Could not generate job data: {e}", main_item.error_thread_id)
		main_item.be_courier_collection = 'Error'
		main_item.commit()
		return main_item

	stuart.client.create_job(job_data)
