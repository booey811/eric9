import os

import monday

import config

conf = config.get_config()

conn = monday.MondayClient(conf.MONDAY_KEYS["gabe"])
