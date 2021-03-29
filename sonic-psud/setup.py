from setuptools import setup

setup(
    name='sonic-psud',
    version='1.0',
    description='PSU daemon for SONiC',
    license='Apache 2.0',
    author='SONiC Team',
    author_email='linuxnetdev@microsoft.com',
    url='https://github.com/Azure/sonic-platform-daemons',
    maintainer='Kevin Wang',
    maintainer_email='kevinw@mellanox.com',
    packages=[
        'tests'
    ],
    scripts=[
        'scripts/psud',
    ],
    setup_requires=[
        'pytest-runner',
        'wheel'
    ],
    tests_require=[
        'mock>=2.0.0; python_version < "3.3"',
        'pytest',
        'pytest-cov',
        'sonic_platform_common'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: No Input/Output (Daemon)',
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
    keywords='sonic SONiC psu PSU daemon psud PSUD',
    test_suite='setup.get_test_suite'
)
