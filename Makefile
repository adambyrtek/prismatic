default: test

test:
	venv/bin/tox prismatic

pypi: clear pypi-register pypi-build pypi-upload

pypi-register:
	python setup.py register -r pypi

pypi-build:
	python setup.py sdist bdist_wheel

pypi-upload:
	venv/bin/twine upload -r pypi dist/*

clear:
	rm -rf build dist
