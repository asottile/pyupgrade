from setuptools import setup

setup(
    name='pyupgrade-opt',
    description='A tool to automatically upgrade syntax for newer versions of Python. '
                'Makes changing % to format() optional - that\'s the killer feature.',
    url='https://github.com/vmarkovtsev/pyupgrade-opt',
    version='1.7.0',
    author='Anthony Sottile, Vadim Markovtsev',
    author_email='asottile@umich.edu, vadim@sourced.tech',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    install_requires=['tokenize-rt>=2.1'],
    py_modules=['pyupgrade_opt'],
    entry_points={'console_scripts': ['pyupgrade-opt = pyupgrade_opt:main']},
)