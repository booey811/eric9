from flask import Blueprint, jsonify

test_bp = Blueprint("test", __name__, url_prefix="/test")


@test_bp.route("/")
def test_index():
	raise Exception("Forced error")
	return jsonify({"success": True}), 200
