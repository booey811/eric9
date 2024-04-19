import logging
import json

from flask import Blueprint, jsonify, request

import config
from ...services import monday
from ...cache.rq import q_low
from ...tasks import monday as mon_tasks

conf = config.get_config()

log = logging.getLogger('eric')

repair_process_bp = Blueprint('repair_process', __name__, url_prefix='/monday/repair-process')


@repair_process_bp.route('/sync-check-items-and-results-columns', methods=['POST'])
@monday.monday_challenge
def sync_check_items_and_results_columns():
	log.debug('Syncing Check Items and Results Columns')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	q_low.enqueue(
		mon_tasks.repair_process.sync_check_items_and_results_columns,
		data['pulseId']
	)

	return jsonify({'message': 'OK'}), 200
