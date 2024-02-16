import time

import config
from ...services.notion import notion_client, notion_utils
from ...services.openai import utils as ai_utils
from ...cache import rq
from ...utilities import notify_admins_of_error

conf = config.get_config()

VOICE_TEXT_DB_ID = "16f011ada2d0444390ec41d14658fa34"
BLOG_ARTICLES_DB_ID = "e76b2be2475147509e15e22037a0ccab"


def submit_voice_summary_for_blog_writing():
	SUCCESS_ENDPOINT = "https://eric9-c2d6de2066d6.herokuapp.com/ai-blogs/process-ai-blog-content"

	db_query = notion_client.databases.query(
		database_id=VOICE_TEXT_DB_ID,
		filter={
			"property": "AI Blog Composition",
			"status": {
				"equals": "Do Now!"
			}
		}
	)

	processed = []

	pages = db_query['results']
	for voice_note_page in pages:

		# create ai blog articles page
		ai_blog_page = notion_client.pages.create(
			parent={
				"type": "database_id",
				"database_id": BLOG_ARTICLES_DB_ID
			},
			properties={
				"Name": {
					"title": [
						{
							"text": {
								"content": str(voice_note_page['properties']['Title']['title'][0]['text']['content'])
							}
						}
					]
				},
				"Source": {
					"relation": [
						{
							"id": voice_note_page['id']
						}
					]
				},
			}
		)

		page_content = notion_utils.get_page_text(voice_note_page['id'])
		run = ai_utils.create_and_run_thread(
			assistant_id=conf.OPEN_AI_ASSISTANTS['blog_writer'],
			metadata={
				"voice_note_page_id": voice_note_page['id'],
				"blog_content_page_id": ai_blog_page['id'],
				"success_endpoint": SUCCESS_ENDPOINT,
			},
			messages=[page_content],
		)

		# update status of the voice note page
		notion_client.pages.update(
			page_id=voice_note_page['id'],
			properties={
				"AI Blog Composition": {
					"status": {
						"name": "Processing"
					}
				}
			}
		)

		if conf.CONFIG == 'DEVELOPMENT':
			while run.status not in ('completed', 'failed'):
				run = ai_utils.fetch_run(run.thread_id, run.id)
				time.sleep(5)
			process_blog_writing_results(
				thread_id=run.thread_id,
				voice_note_page_id=voice_note_page['id'],
				blog_content_page_id=ai_blog_page['id']
			)
		else:
			rq.q_ai_results.enqueue(
				ai_utils.check_run,
				kwargs={
					"thread_id": run.thread_id,
					"run_id": run.id,
					"success_endpoint": SUCCESS_ENDPOINT,
				}
			)

	return processed


def process_blog_writing_results(thread_id, run_id, voice_note_page_id, blog_content_page_id):
	# append child blocks of paragraphs to page
	messages = ai_utils.list_messages(thread_id, limit=20)

	# get the content from the run
	content = messages.data[0].content[0].text.value

	children = [
		{
			"object": "block",
			"type": "table_of_contents",
			"table_of_contents": {
				"color": "default"
			}
		}
	]
	lines = content.split("\n")
	for line in lines:
		if line.startswith("##"):
			# it's a sub-heading
			children.append({
				"object": "block",
				"type": "heading_2",
				"heading_2": {
					"rich_text": [{"type": "text", "text": {"content": line[2:].replace("#", "").strip()}}]
				}
			})
		elif line.startswith("#"):
			# it's a main heading
			children.append({
				"object": "block",
				"type": "heading_1",
				"heading_1": {
					"rich_text": [{"type": "text", "text": {"content": line[1:].replace("#", "").strip()}}]
				}
			})
		else:
			# it's a paragraph
			children.append({
				"object": "block",
				"type": "paragraph",
				"paragraph": {
					"rich_text": [{"type": "text", "text": {"content": line.replace("#", "").strip()}}]
				}
			})

	notion_client.blocks.children.append(
		block_id=blog_content_page_id,
		children=children
	)

	chunked_content = content.split(" ")

	run = ai_utils.fetch_run(thread_id, run_id)
	cost_dict = {
		"gpt-4": {
			"in": 0.03,
			"out": 0.06
		},
		"gpt-3": {
			"in": 0.0005,
			"out": 0.0015
		}
	}
	total_cost = 0
	try:
		for m in cost_dict:
			if run.model.lower() in m:
				costs = cost_dict[m]
				in_cost = costs['in']/1000 * run.usage.prompt_tokens
				out_cost = costs['out']/1000 * run.usage.completion_tokens
				total_cost = in_cost + out_cost
	except Exception as e:
		notify_admins_of_error(
			f"Error calculating cost for AI blog composition: {e}"
		)
		total_cost = 0

	notion_client.pages.update(
		page_id=blog_content_page_id,
		properties={
			"Number of Words": {
				"number": len(chunked_content)
			}
		}
	)
	notion_client.pages.update(
		page_id=voice_note_page_id,
		properties={
			"AI Blog Composition": {
				"status": {
					"name": "Done"
				}
			},
			"Cost": {
				"number": total_cost
			}
		}
	)

	return content
