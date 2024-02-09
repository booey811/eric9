# from ..services import slack
# from ..errors import EricError
#
#
# from .. import conf
#
#
# class ErrorInRoute(EricError):
#
# 	def __init__(self, e, route_path):
# 		self.e = e
# 		self.path = route_path
#
# 		slack_blocks = [
# 			slack.blocks.add.text_block(f'Error in Route {str(self.path)}'),
# 			slack.blocks.add.text_block(str(self.e))
# 		]
#
# 		slack.slack_client.chat_postMessage(
# 			channel=conf.SLACK_DEV_CHANNEL,
# 			text='Route Error',
# 			blocks=slack_blocks
# 		)
#
# 	def __str__(self):
# 		return f"Error in Route({self.path}): {str(self.e)}"
