import os
from setuptools import setup

def read(*paths):
    with open(os.path.join(*paths), 'r') as f:
        return f.read()

setup(
  name='prismatic',
  packages=['prismatic'],
  install_requires=['isodate'],
  version='0.4',
  description='Serialization between JSON dicts and data objects designed for REST APIs',
  long_description=read('README.rst'),
  license='MIT',
  author='Adam Byrtek',
  author_email='adambyrtek@gmail.com',
  url='https://github.com/adambyrtek/prismatic',
  keywords=['json', 'orm', 'serialization', 'api', 'rest'],
  classifiers=[],
)
