import logging
from flask import Blueprint, request, jsonify
import json

from ...cache.rq import q_low
from ...services import monday
from ...tasks.monday import stock_control as stock_tasks

log = logging.getLogger('eric')

stock_control_bp = Blueprint('monday_stock_control', __name__)

@stock_control_bp.route("/orders/process", methods=['POST'])
@monday.monday_challenge
def process_order():
	log.debug('Handling Main Board Main Status Change')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']
	q_low.enqueue(
		stock_tasks.process_complete_order_item,
		data['pulseId']
	)
	return jsonify({'status': 'ok'}), 200
