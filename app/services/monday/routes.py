import logging

from quart import Blueprint, jsonify, request

log = logging.getLogger('eric')

test_bp = Blueprint('test', __name__, url_prefix='/test')


@test_bp.route("/")
async def index():
	log.debug('test index route')
	return jsonify({'success': True, 'route': request.url})


@test_bp.route('/logs')
async def test_logs():
	log.debug('DEBUG LOG')
	log.info('INFO LOG')
	return jsonify(request.url)
