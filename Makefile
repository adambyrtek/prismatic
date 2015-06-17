default: test

test:
	tox

pypi: pypi-register pypi-upload

pypi-register:
	python setup.py register -r pypi

pypi-upload:
	python setup.py sdist upload -r pypi
	python setup.py bdist_wheel upload -r pypi
