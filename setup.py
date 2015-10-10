from setuptools import find_packages, setup


setup(
    name='tchannel',
    version='0.17.3',
    author='Abhinav Gupta, Aiden Scandella, Bryce Lampe, Grayson Koonce, Junchao Wu',
    author_email='abg@uber.com',
    description='Network multiplexing and framing protocol for RPC',
    license='MIT',
    url='https://github.com/uber/tchannel-python',
    packages=find_packages(exclude=['tests', 'tests.*']),
    package_data={
        '': ['*.thrift'],
    },
    install_requires=[
        'contextlib2',
        'crcmod',
        'tornado>=4.0,<5.0',
        'toro>=0.8,<0.9',
        'thriftrw>=0.3,<0.5',
        'threadloop>=0.5,<0.6',
        'futures',
    ],
    extras_require={
        'vcr': ['PyYAML', 'mock', 'wrapt'],
    },
    entry_points={
        'console_scripts': [
            'tcurl.py = tchannel.tcurl:start_ioloop'
        ]
    },
)
