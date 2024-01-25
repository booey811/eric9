import pytest
import json
from flask_testing import TestCase
from app import create_app  # replace with your actual application import
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
	app = create_app()  # replace with your actual application setup
	app.config['TESTING'] = True
	with app.test_client() as client:
		yield client


@pytest.fixture
def monday_webhook_update_created():
	return {
		"event": {
			"app": "monday",
			"type": "create_update",
			"triggerTime": "2024-01-23T15:35:02.017Z",
			"subscriptionId": 308335711,
			"userId": 12304876,
			"originalTriggerUuid": None,
			"boardId": 349212843,
			"pulseId": 5892566890,
			"body": "Battery Drain Results<br><br>Battery Drain Test Results<br><br>Rate: 4.2% per hour<br>:Conditions: Replaced Battery",
			"textBody": "Battery Drain Results\n\nBattery Drain Test Results\n\nRate: 4.2% per hour\n:Conditions: Replaced Battery",
			"updateId": 2715253913,
			"replyId": 2731385536,
			"triggerUuid": "79af6172230a2128765c915c20df9012"
		}
	}


def test_process_ai_translation_request(client, monday_webhook_update_created):
	response = client.post(
		'/ai/request-translation/',
		data=json.dumps(monday_webhook_update_created),
		content_type='application/json'
	)
	assert response.status_code == 200


def test_process_ai_translation(client):
	with patch('app.routes.ai_routes.q_high.enqueue') as mock_enqueue, \
			patch('app.routes.ai_routes.ai.list_messages') as mock_list_messages:

		mock_message = MagicMock()
		mock_message.content[0].text.value = 'Mock message'
		mock_list_messages.return_value.data = [mock_message]

		response = client.post(
			'/ai/translator-results/',
			data=json.dumps({
				"thread_id": "TEST_THREAD_ID",
				"notes_thread": "TEST_NOTES_THREAD_ID",
				"main_id": 12345678,
			}),
			content_type='application/json'
		)
		assert response.status_code == 200
		mock_enqueue.assert_called_once()
		mock_list_messages.assert_called_once()
