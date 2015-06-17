default: test

test:
	venv/bin/py.test prismatic

pypi-upload:
	python setup.py sdist upload -r pypi
