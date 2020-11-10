from setuptools import setup

setup(
    name='sonic-chassisd',
    version='1.0',
    description='Chassis daemon for SONiC',
    license='Apache 2.0',
    author='SONiC Team',
    author_email='linuxnetdev@microsoft.com',
    url='https://github.com/Azure/sonic-platform-daemons',
    maintainer='Manju Prabhu',
    maintainer_email='manjunath.prabhu@nokia.com',
    packages=[
        'tests'
    ],
    scripts=[
        'scripts/chassisd',
    ],
    setup_requires= [
        'pytest-runner',
        'wheel'
    ],
    tests_require = [
        'pytest',
        'mock>=2.0.0',
        'pytest-cov'
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
    keywords='sonic SONiC chassis Chassis daemon chassisd',
    test_suite='setup.get_test_suite'
)
