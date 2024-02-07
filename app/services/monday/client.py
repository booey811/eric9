import os

import monday

from app import config

conf = config.get_config()

client = monday.MondayClient(conf.MONDAY_KEYS["gabe"])
