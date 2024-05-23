import datetime
import time

import config

from ....services.openai import utils as ai_utils
from ....services import slack, monday
from ....cache.rq import q_ai_results

conf = config.get_config()


def check_run(thread_id, run_id, channel_id, status_message_ts):
	run = ai_utils.fetch_run(thread_id, run_id)
	try:
		if run.status == "completed":
			recent_message = ai_utils.list_messages(thread_id, 1, run.id).data[0].content[0].text.value
			slack.slack_app.client.chat_update(
				channel=channel_id,
				text=recent_message,
				ts=status_message_ts
			)
			try:
				thread_store = monday.items.ai_threads.InvoiceAssistantThreadItem.get_by_thread_id(thread_id)
				prompt_cost = int(run.usage.prompt_tokens) * 0.0000001 * 5  # gpt-4o PROMPT: $5.00/1M tokens
				output_cost = int(run.usage.completion_tokens) * 0.0000001 * 15  # gpt-4o PROMPT: $5.00/1M tokens
				total_cost = max(prompt_cost + output_cost, 0.01)  # 0.01 is the minimum we can be physically charged

				update = f"""RUN INFO\n\n{recent_message}\n\nPrompt Tokens: {run.usage.prompt_tokens}
				Output Tokens: {run.usage.completion_tokens}\nTotal Cost: ${total_cost:.2f} ({run.model})"""

				thread_store.add_update(update)

				running_cost = thread_store.running_cost.value
				if not running_cost:
					running_cost = 0

				running_cost += total_cost
				thread_store.running_cost = running_cost
				thread_store.commit()

			except monday.api.items.MondayAPIError as e:
				pass

		elif run.status in ('running', 'queued', 'in_progress'):
			# job still being completed, requeue
			slack.slack_app.client.chat_update(
				channel=channel_id,
				text=f"Thread is still running, status: {run.status}",
				ts=status_message_ts
			)
			if conf.CONFIG == 'PRODUCTION':
				q_ai_results.enqueue_in(
					time_delta=datetime.timedelta(seconds=5),
					func=check_run,
					kwargs={
						"thread_id": thread_id,
						"run_id": run.id,
						"status_message_ts": status_message_ts,
						"channel_id": channel_id
					}
				)
			else:
				time.sleep(2)
				check_run(thread_id, run_id, channel_id, status_message_ts)
			return run
		elif run.status == 'failed':
			raise ai_utils.InvalidRunStatus(run_id, thread_id, run.status)
		else:
			raise ai_utils.InvalidRunStatus(run_id, thread_id, run.status)

	except Exception as e:
		slack.slack_app.client.chat_update(
			channel=channel_id,
			text=f"Run has failed: {str(e)}",
			ts=status_message_ts
		)
		raise e
