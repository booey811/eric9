from flask import Blueprint, jsonify, request
import json

from ...services import monday
from ...tasks.monday import sales as sales_tasks
from ...cache.rq import q_high, q_low

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


@monday_sales_bp.route('/re-process-sales-ledger-item', methods=['POST'])
@monday.monday_challenge
def re_process_sales_ledger_item():
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']
	sale_id = data['pulseId']

	q_low.enqueue(
		sales_tasks.create_or_update_sales_ledger_item,
		sale_id
	)

	return jsonify({'message': 'OK'}), 200


@monday_sales_bp.route('/manual-sale-creation-request', methods=['POST'])
@monday.monday_challenge
def manual_creation_of_sale_item_requested():
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	main_id = data['pulseId']

	q_high.enqueue(
		sales_tasks.create_or_update_sale,
		args=(main_id, True)
	)

	return jsonify({'message': 'OK'}), 200


@monday_sales_bp.route("/generate-invoice-item", methods=["POST"])
@monday.monday_challenge
def add_line_to_invoice_item():
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	sale_item_id = data['pulseId']

	q_high.enqueue(
		sales_tasks.generate_invoice_from_sale,
		sale_item_id
	)

	return jsonify({'message': 'OK'}), 200


@monday_sales_bp.route("/sync-invoice-to-xero", methods=["POST"])
@monday.monday_challenge
def sync_invoice_to_xero():
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	invoice_item_id = data['pulseId']

	q_high.enqueue(
		sales_tasks.sync_invoice_data_to_xero,
		invoice_item_id
	)

	return jsonify({'message': 'OK'}), 200


@monday_sales_bp.route("/convert-to-pl-item", methods=["POST"])
@monday.monday_challenge
def add_item_to_pl_board():
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	q_low.enqueue(
		sales_tasks.convert_sale_to_profit_and_loss,
		data['pulseId']
	)
	return jsonify({'message': 'OK'}), 200


@monday_sales_bp.route("/process-pl-item", methods=["POST"])
@monday.monday_challenge
def process_pl_item():
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	q_low.enqueue(
		sales_tasks.calculate_profit_and_loss,
		data['pulseId']
	)

	return jsonify({'message': 'OK'}), 200
