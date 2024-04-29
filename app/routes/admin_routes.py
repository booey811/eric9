import logging
import json

from flask import Blueprint, request, jsonify

from ..services.monday import monday_challenge, items
from ..services import monday
from ..services.motion import MotionClient, MotionError
from ..utilities import users
from ..cache.rq import q_high
from ..tasks import scheduling

log = logging.getLogger('eric')

admin_bp = Blueprint('admin', __name__, url_prefix="/admin")


@admin_bp.route('/refresh-cache', methods=['POST'])
def refresh_cache():
	"""
	Refresh the cache for the application
	"""
	from ..cache import utilities
	q_high.enqueue(utilities.build_part_cache)
	q_high.enqueue(utilities.build_product_cache)
	q_high.enqueue(utilities.build_device_cache)
	q_high.enqueue(utilities.build_pre_check_cache)
	return True


@admin_bp.route('/motion-reschedule', methods=['POST'])
def force_reschedule():
	"""
	Force a reschedule of all items
	"""
	from ..tasks import scheduling
	all_users = [users.User(_) for _ in ['safan', 'andres', 'ferrari']]
	for user in all_users:
		q_high.enqueue(scheduling.schedule_update, user.repair_group_id)