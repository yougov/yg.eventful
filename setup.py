from setuptools import setup

setup_params = dict(
	name="eventful",
	version="1.0.8",
	url="http://dev.yougov.com/G",
	author="Jamie Turner",
	author_email="dev@yougov.com",
	packages=["eventful", "eventful.proto"],
)

if __name__ == '__main__':
	setup(**setup_params)
