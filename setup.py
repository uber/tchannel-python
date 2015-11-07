from setuptools import find_packages, setup


setup(
    name='tchannel',
    version='0.19.1.dev0',
    author=', '.join([
        'Abhinav Gupta',
        'Aiden Scandella',
        'Bryce Lampe',
        'Grayson Koonce',
        'Junchao Wu',
    ]),
    author_email='abg@uber.com',
    description='Network multiplexing and framing protocol for RPC',
    license='MIT',
    url='https://github.com/uber/tchannel-python',
    packages=find_packages(exclude=['tests', 'tests.*']),
    package_data={
        '': ['*.thrift'],
    },
    install_requires=[
        # stdlib backports, no constraints needed
        'contextlib2',

        # external deps
        'crcmod>=1,<2',
        'tornado>=4.2,<5',

        # tchannel deps
        'thriftrw>=1,<2',
        'threadloop>=1,<2',
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
