from setuptools import setup

setup(
    name='pyupgrade',
    description='A tool to automatically upgrade syntax for newer versions.',
    url='https://github.com/asottile/pyupgrade',
    version='1.9.0',
    author='Anthony Sottile',
    author_email='asottile@umich.edu',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    install_requires=['tokenize-rt>=2.1'],
    py_modules=['pyupgrade'],
    entry_points={'console_scripts': ['pyupgrade = pyupgrade:main']},
)
