import os

import app

if __name__ == '__main__':
	eric = app.create_app()
	env = os.getenv('ENV')
	if env == 'development':
		pass
	elif env == 'production':
		eric.run()
	else:
		raise Exception(f"Invalid ENV: {env}")
