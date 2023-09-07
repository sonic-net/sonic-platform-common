from setuptools import setup

setup(
    name='sonic-sensormond',
    version='1.0',
    description='Sensor Monitor daemon for SONiC',
    license='Apache 2.0',
    author='SONiC Team',
    author_email='linuxnetdev@microsoft.com',
    url='https://github.com/Azure/sonic-platform-daemons',
    maintainer='Mridul Bajpai',
    maintainer_email='mridul@cisco.com',
    packages=[
        'tests'
    ],
    scripts=[
        'scripts/sensormond',
    ],
    setup_requires=[
        'pytest-runner',
        'wheel'
    ],
    tests_require=[
        'mock>=2.0.0; python_version < "3.3"',
        'pytest',
        'pytest-cov',
        'sonic-platform-common'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.7',
        'Topic :: System :: Hardware',
    ],
    keywords='sonic SONiC SENSORMONITOR sensormonitor SENSORMON sensormon sensormond',
    test_suite='setup.get_test_suite'
)
