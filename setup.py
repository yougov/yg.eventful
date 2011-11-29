from setuptools import setup

setup_params = dict(
	name="eventful",
	use_hg_version=True,
	url="http://dev.yougov.com/G",
	author="Jamie Turner",
	author_email="dev@yougov.com",
	packages=["eventful", "eventful.proto"],
	setup_requires=[
		'hgtools',
	],
)

if __name__ == '__main__':
	setup(**setup_params)
