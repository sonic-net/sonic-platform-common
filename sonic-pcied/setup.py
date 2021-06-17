from setuptools import setup

setup(
    name='sonic-pcied',
    version='1.0',
    description='PCIe check daemon for SONiC',
    license='Apache 2.0',
    author='SONiC Team',
    author_email='linuxnetdev@microsoft.com',
    url='https://github.com/Azure/sonic-platform-daemons',
    maintainer='Sujin Kang',
    maintainer_email='sujkang@microsoft.com',
    scripts=[
        'scripts/pcied',
    ],
    setup_requires=[
        'pytest-runner',
        'wheel'
    ],
    install_requires=[
        'enum34; python_version < "3.4"',
        'sonic-py-common',
    ],
    tests_requires=[
        'mock>=2.0.0; python_version < "3.3"',
        'pytest',
        'pytest-cov',
        'sonic-platform-common'
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
    keywords='sonic SONiC PCIe pcie PCIED pcied',
    test_suite='setup.get_test_suite'
)
