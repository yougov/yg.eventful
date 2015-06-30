#!/usr/bin/env python
# Generated by jaraco.develop 2.20
# https://pypi.python.org/pypi/jaraco.develop

import io
import sys

import setuptools

with io.open('README.txt', encoding='utf-8') as readme:
	long_description = readme.read()

needs_pytest = {'pytest', 'test'}.intersection(sys.argv)
pytest_runner = ['pytest_runner'] if needs_pytest else []
needs_sphinx = {'release', 'build_sphinx', 'upload_docs'}.intersection(sys.argv)
sphinx = ['sphinx'] if needs_sphinx else []

setup_params = dict(
	name='yg.eventful',
	use_scm_version=True,
	author="Jamie Turner",
	author_email="dev@yougov.com",
	description="A library to facilitate pyevent stuff",
	long_description=long_description,
	url="https://yougov.kilnhg.com/Code/Repositories/support/yg-eventful",
	packages=setuptools.find_packages(),
	include_package_data=True,
	namespace_packages=['yg'],
	install_requires=[
		'event',
	],
	extras_require={
	},
	setup_requires=[
		'setuptools_scm',
	] + pytest_runner + sphinx,
	tests_require=[
		'pytest',
	],
	classifiers=[
		"Development Status :: 5 - Production/Stable",
		"Intended Audience :: Developers",
		"License :: OSI Approved :: MIT License",
		"Programming Language :: Python :: 2.7",
	],
	entry_points={
	},
)
if __name__ == '__main__':
	setuptools.setup(**setup_params)
