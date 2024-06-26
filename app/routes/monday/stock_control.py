import logging
from flask import Blueprint, request, jsonify
import json

from ...cache.rq import q_low
from ...services import monday
from ...tasks.monday import stock_control as stock_tasks

log = logging.getLogger('eric')

stock_control_bp = Blueprint('monday_stock_control', __name__, url_prefix="/monday/stock-control")


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


@stock_control_bp.route("/counts/process-completed-count", methods=['POST'])
@monday.monday_challenge
def process_completed_count():
	log.debug('Handling Main Board Main Status Change')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	q_low.enqueue(
		stock_tasks.process_completed_count_item,
		data['pulseId']
	)
	return jsonify({'status': 'ok'}), 200


@stock_control_bp.route("/stock-profile-creation", methods=['POST'])
@monday.monday_challenge
def build_stock_profile():
	log.debug('Checking out repair stock')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	sc_item_id = data['pulseId']
	sc_item = monday.items.part.StockCheckoutControlItem(sc_item_id)
	main_id = sc_item.main_item_id.value
	if main_id:
		q_low.enqueue(
			stock_tasks.update_stock_checkouts,
			main_id
		)
	return jsonify({'status': 'ok'}), 200


@stock_control_bp.route("/stock-checkout-adjustment", methods=['POST'])
@monday.monday_challenge
def checkout_stock_profile():
	log.debug('Checking out repair stock')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	item_id = data['pulseId']
	if item_id:
		q_low.enqueue(
			stock_tasks.process_stock_checkout,
			item_id
		)
	return jsonify({'status': 'ok'}), 200


@stock_control_bp.route("/add-part-to-pending-orders", methods=['POST'])
@monday.monday_challenge
def add_part_to_pending_orders():
	log.debug('Adding part to pending orders')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	item_id = data['pulseId']
	if item_id:
		q_low.enqueue(
			stock_tasks.add_part_to_order,
			item_id
		)
	return jsonify({'status': 'ok'}), 200


@stock_control_bp.route("/process-refurb-output", methods=['POST'])
@monday.monday_challenge
def process_refurb_output_item():
	log.debug('Processing Refurb Output')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	item_id = data['pulseId']
	if item_id:
		q_low.enqueue(
			stock_tasks.process_refurb_output_item,
			item_id
		)
	return jsonify({'status': 'ok'}), 200


@stock_control_bp.route("/process-refurb-output-components", methods=['POST'])
@monday.monday_challenge
def process_refurb_output_components():
	log.debug('Processing Refurb Output Components')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	item_id = data['pulseId']
	if item_id:
		q_low.enqueue(
			stock_tasks.process_refurb_consumption,
			item_id
		)
	return jsonify({'status': 'ok'}), 200


@stock_control_bp.route("/handle-waste-stock-adjustment", methods=['POST'])
@monday.monday_challenge
def handle_waste_stock_adjustment():
	log.debug('Handling Waste Stock Adjustment')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	item_id = data['pulseId']
	if item_id:
		q_low.enqueue(
			stock_tasks.handle_waste_stock_adjustment,
			item_id
		)
	return jsonify({'status': 'ok'}), 200
