from ...services.slack.flows import get_flow


def process_repair_view_submission(metadata):
	"""Processes the data from a repair view submission"""

	flow_controller = get_flow(metadata['flow'], None, None, None, metadata)
	flow_controller.end_flow()
