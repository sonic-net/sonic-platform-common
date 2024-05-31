from setuptools import setup

setup(
    name='sonic-stormond',
    version='1.0',
    description='Storage Device Monitoring Daemon for SONiC',
    license='Apache 2.0',
    author='SONiC Team',
    author_email='linuxnetdev@microsoft.com',
    url='https://github.com/sonic-net/sonic-platform-daemons',
    maintainer='Ashwin Srinivasan',
    maintainer_email='assrinivasan@microsoft.com',
    scripts=[
        'scripts/stormond',
    ],
    setup_requires=[
        'pytest-runner',
        'wheel'
    ],
    install_requires=[
        'enum34',
        'sonic-py-common',
    ],
    tests_require=[
        'mock>=2.0.0',
        'pytest',
        'pytest-cov',
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
        'Topic :: System :: Hardware',
    ],
    keywords='sonic SONiC ssd Ssd SSD ssdmond storage stormond storagemond',
    test_suite='setup.get_test_suite'
)
