import re
import ast
from setuptools import setup

_version_re = re.compile(r'__version__\s+=\s+(.*)')
with open('drowsy/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

with open("requirements.txt") as f:
    requirements = f.read().splitlines()
with open("requirements_test.txt") as f:
    test_requirements = f.read().splitlines()
setup_requirements = test_requirements

setup(
    name='Drowsy',
    version=version,
    url='https://github.com/repole/drowsy',
    download_url="https://github.com/repole/drowsy/tarball/" + version,
    license='MIT',
    author='Nicholas Repole',
    author_email='n.repole@gmail.com',
    description='A set of SQLAlchemy tools for building RESTful services.',
    packages=['drowsy'],
    platforms='any',
    test_suite='tests',
    tests_require=test_requirements,
    install_requires=requirements,
    setup_requires=setup_requirements,
    keywords=['sqlalchemy', 'marshmallow', 'RESTful'],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Database :: Front-Ends",
        "Operating System :: OS Independent"
    ]
)
