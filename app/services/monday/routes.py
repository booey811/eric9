from quart import Blueprint, jsonify, request

blueprint = Blueprint('tests', __name__)


@blueprint.route("/", methods=['GET', 'POST'])
async def index():
	print('HIT ROUTE')
	return jsonify({'success': True, 'route': request.url})