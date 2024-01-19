import logging
import os

from flask import Blueprint, jsonify, request, current_app, url_for

log = logging.getLogger("eric")

test_bp = Blueprint("test", __name__, url_prefix="/test")


@test_bp.route("/")
def test_index():
	response = jsonify({"success": True, "path": request.path}), 200
	return response


@test_bp.route("/site-map")
def site_map():
	if os.environ['ENV'] != ('development', 'testing'):
		return jsonify({'success': False, 'message': 'This route is only available in development mode'})
	log.debug("Registered routes:")
	with current_app.app_context():  # Use app_context instead of test_request_context
		for rule in current_app.url_map.iter_rules():
			line = f"{rule.endpoint}: "
			if 'GET' in rule.methods:
				line += f"GET {url_for(rule.endpoint, **(rule.defaults or {}))} "
			if 'POST' in rule.methods:
				line += f"POST "
			# Add other methods if needed
			log.debug(line)
	return jsonify({'success': True, 'message': 'Check console for registered routes'})
