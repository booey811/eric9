import os

import moncli

moncli.api.api_key = os.environ['MON-SYSTEM']

client = moncli.client