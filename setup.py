#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'Click>=6.0',
    'rdflib>=4.2.1',
    'pyxdg>=0.25',
    'GitPython>=2.0.8',
    'mercurial>=3.7.3',
]

test_requirements = [
    # TODO: put package test requirements here
]

dependency_links = [
    'git+https://anongit.freedesktop.org/git/xdg/pyxdg.git#egg=pyxdg-0.25'
]

setup(
    name='workspace-hygiene',
    version='0.1.0',
    description="Scan your workspace for file changes and dirty version control repositories.",
    long_description=readme + '\n\n' + history,
    author="Dorian Taylor",
    author_email='dorian.taylor.lists@gmail.com',
    url='https://github.com/doriantaylor/workspace-hygiene',
    packages=[
        'workspace-hygiene',
    ],
    package_dir={'workspace-hygiene': 'wshygiene'},
    entry_points={
        'console_scripts': [
            'workspace-hygiene=wshygiene.cli:main'
        ]
    },
    include_package_data=True,
    install_requires=requirements,
    dependency_links=dependency_links,
    license="Apache Software License 2.0",
    zip_safe=False,
    keywords='workspace-hygiene',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
