import os

import app

if __name__ == '__main__':
	eric = app.create_app()
	env = os.getenv('ENV')
	if env == 'production':
		eric.run()

	if env == 'development':
		pass
	else:
		raise Exception(f"Invalid ENV: {env}")
