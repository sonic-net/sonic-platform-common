from setuptools import setup

setup(
    name='sonic-thermalctld',
    version='1.0',
    description='Thermal control daemon for SONiC',
    license='Apache 2.0',
    author='SONiC Team',
    author_email='linuxnetdev@microsoft.com',
    url='https://github.com/Azure/sonic-platform-daemons',
    maintainer='Junchao Chen',
    maintainer_email='junchao@mellanox.com',
    packages=[
        'tests'
    ],
    scripts=[
        'scripts/thermalctld',
    ],
    setup_requires= [
        'pytest-runner'
    ],
    tests_require = [
        'pytest',
        'mock>=2.0.0'
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
        'Topic :: System :: Hardware',
    ],
    keywords='sonic SONiC THERMALCONTROL thermalcontrol THERMALCTL thermalctl thermalctld',
    test_suite='setup.get_test_suite'
)
