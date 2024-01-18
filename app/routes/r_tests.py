from flask import Blueprint, jsonify, request

test_bp = Blueprint("test", __name__, url_prefix="/test")


@test_bp.route("/")
def test_index():
	return jsonify({"success": True, "path": request.path}), 200
