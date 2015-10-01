"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/Livefyre/awscensus
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name='awscensus',
    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='0.8',
    description='Tools to gather usage information in AWS',
    # The project's main homepage.
    url='https://github.com/Livefyre/awscensus',

    # Author details
    author='Nicholas Fowler',
    author_email='nfowler@livefyre.com',

    # What does your project relate to?
    keywords='aws ec2 reap census reserved instances',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=['py-yacc','boto','docopt', 'requests', 'simplejson','demjson', 'six', 'unicodecsv'],
    dependency_links=['git+ssh://git@github.com/andrewguy9/csvorm.git@float#egg=csvorm-float'],

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    package_data={
        'aws': ['app.yaml'],
    },

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'reap=reap:main',
            'awscensus=awscensus:main',
            'billing=billing:main',
            'snapcleaner=snapcleaner:main',
        ],
    },
)
