default: test

test:
	venv/bin/py.test prismatic

pypi: pypi-register pypi-upload

pypi-register:
	python setup.py register -r pypi

pypi-upload:
	python setup.py sdist upload -r pypi
