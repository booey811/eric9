import os

import monday

import config
from ....errors import EricError

conf = config.get_config()

conn = monday.MondayClient(conf.MONDAY_KEYS["gabe"])


class MondayAPIError(EricError):
	pass
