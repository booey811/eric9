from flask import Blueprint, request, jsonify

from ...tasks.notion import ai_blogs
from ...cache import rq

ai_blogs_bp = Blueprint('ai_blogs', __name__, url_prefix='/ai-blogs')


@ai_blogs_bp.route("/submit-voice-summary", methods=["POST"])
def submit_voice_summary_for_blog_writing():
	rq.q_high.enqueue(
		ai_blogs.submit_voice_summary_for_blog_writing
	)

	return jsonify({
		"status": "success",
		"message": "Voice summary submitted for blog writing."
	})


@ai_blogs_bp.route("/process-ai-blog-content", methods=["POST"])
def process_ai_blog_content():
	json_data = request.get_json()

	rq.q_high.enqueue(
		ai_blogs.process_blog_writing_results,
		kwargs={
			"run_id": json_data['run_id'],
			"thread_id": json_data['thread_id'],
			"voice_note_page_id": json_data['metadata']['voice_note_page_id'],
			"blog_content_page_id": json_data['metadata']['blog_content_page_id']
		}
	)

	return jsonify({
		"status": "success",
		"message": "AI blog content processing initiated."
	})