import logging
from flask import Blueprint, jsonify, request
import json

from ...cache.rq import q_low, q_high
from ...services import monday
from ...tasks.monday import web_bookings, product_management, sales, misc, repair_process
from ...tasks import sync_platform
from ...utilities import notify_admins_of_error
import config

conf = config.get_config()

log = logging.getLogger('eric')

monday_misc_bp = Blueprint('monday_misc', __name__, url_prefix='/monday/misc')


@monday_misc_bp.route('/enquiry', methods=['POST'])
@monday.monday_challenge
def push_web_enquiry_to_zendesk():
	log.debug('Handling Main Board Main Status Change')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	if conf.CONFIG in ("DEVELOPMENT", "TESTING"):
		web_bookings.push_web_enquiry_to_zendesk(data['pulseId'])
	else:
		q_low.enqueue(
			web_bookings.push_web_enquiry_to_zendesk,
			data['pulseId']
		)

	return jsonify({'message': 'OK'}), 200


@monday_misc_bp.route('/info-sync', methods=['POST'])
@monday.monday_challenge
def sync_item_with_external_services():
	log.debug('Handling Main Board Data Change')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	if conf.CONFIG in ("DEVELOPMENT", "TESTING"):
		sync_platform.sync_to_external_corporate_boards(data['pulseId'])
	else:
		q_low.enqueue(
			sync_platform.sync_to_external_corporate_boards,
			data['pulseId']
		)

	return jsonify({'message': 'OK'}), 200


@monday_misc_bp.route('/add-woocommerce-order-to-monday', methods=['POST'])
def process_woo_order():
	log.debug('Processing WooCommerce Order')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	try:
		data = json.loads(data)
		item = monday.items.misc.WebBookingItem()
		item.woo_commerce_order_id = str(data['id'])
		item.create(data['billing']['first_name'])
	except Exception as e:
		log.error(f"Error processing WooCommerce Order: {e}")
		notify_admins_of_error(f"Error processing WooCommerce Order: {e}\n\n{type(data)}\n{data}")
		return jsonify({'message': 'OK'}), 200

	item.add_update(json.dumps(data, indent=4))

	return jsonify({'message': 'OK'}), 200


@monday_misc_bp.route('/adjust-web-price', methods=["POST"])
@monday.monday_challenge
def adjust_web_price():
	log.debug('Processing WooCommerce Order')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	if int(data['userId']) == 12304876:  # systems manager (change created by system)
		return jsonify({'message': 'OK'}), 200

	product_id = data.get('pulseId')
	new_price = data['value']['value']
	old_price = data.get('previousValue')
	if old_price:
		old_price = old_price.get('value')
	user_id = data.get('userId')

	q_high.enqueue(
		product_management.adjust_web_price,
		kwargs={
			"product_id": product_id,
			"new_price": new_price,
			"old_price": old_price,
			"user_id": user_id
		}
	)

	return jsonify({'message': 'OK'}), 200


@monday_misc_bp.route('/battery-test-results', methods=["POST"])
@monday.monday_challenge
def print_battery_results_to_main_item():
	log.debug('Printing Battery Test Results to Main Item')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	q_high.enqueue(
		misc.print_battery_test_results_to_main_item,
		data['pulseId']
	)

	return jsonify({'message': 'OK'}), 200


@monday_misc_bp.route('/convert-to-new-sales', methods=["POST"])
@monday.monday_challenge
def convert_financial_item_to_sales():
	from dateutil.parser import parse
	log.debug('Converting old financial item to new sales item')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']
	financial_id = data['pulseId']

	financial_data = monday.api.get_api_items([int(financial_id)])[0]

	main_id_col = [c for c in financial_data['column_values'] if c['id'] == "mainboard_id6"][0]
	date_col = [c for c in financial_data['column_values'] if c['id'] == "date3"][0]

	main_id = main_id_col['text']
	date_added = date_col['text']

	q_low.enqueue(
		sales.create_or_update_sale,
		kwargs={
			"main_id": main_id,
		}
	)

	return jsonify({'message': 'OK'}), 200


@monday_misc_bp.route('/sync-check-item-to-results-column', methods=["POST"])
@monday.monday_challenge
def create_new_check_results_column():
	log.debug('Responding to new item in checks board')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	q_low.enqueue(
		repair_process.sync_check_items_and_results_columns,
		data['pulseId']
	)

	return jsonify({'message': 'OK'}), 200
