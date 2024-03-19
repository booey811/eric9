from flask import Blueprint, jsonify, request
import json

from ...services import monday
from ...tasks.monday import sales as sales_tasks
from ...cache.rq import q_high

monday_sales_bp = Blueprint('monday_sales', __name__, url_prefix='/monday/financial')


@monday_sales_bp.route('/re-process-sales-item', methods=['POST'])
@monday.monday_challenge
def re_process_sales_item():
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	sales_control_id = data['pulseId']
	api_data = monday.api.get_api_items([sales_control_id])[0]

	main_id = [c for c in api_data['column_values'] if c['id'] == 'text'][0]['text']

	q_high.enqueue(
		sales_tasks.create_or_update_sale,
		main_id
	)

	return jsonify({'message': 'OK'}), 200
