import requests

from . import helpers


def send_request(url):
	headers = {
		'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
					  'Chrome/88.0.4324.150 Safari/537.36'
	}
	response = requests.get(url=url, verify=False, headers=headers)
	if response.status_code == 200:
		result = response.json()
		status = result.get("status")
		if not status:
			raise ValueError(f"No Status in SickW Response: {result}")
		elif status == "error":
			raise ValueError(result['result'])
		else:
			return result['result']

	else:
		raise ValueError(f"SickW API Fetch Error: {response.text}")
