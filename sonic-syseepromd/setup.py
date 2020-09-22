from setuptools import setup

setup(
    name='sonic-syseepromd',
    version='1.0',
    description='Syseeprom gathering daemon for SONiC',
    license='Apache 2.0',
    author='SONiC Team',
    author_email='linuxnetdev@microsoft.com',
    url='https://github.com/Azure/sonic-platform-daemons',
    maintainer='Kebo Liu',
    maintainer_email='kebol@mellanox.com',
    scripts=[
        'scripts/syseepromd',
    ],
    setup_requires= [
        'wheel'
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
    keywords='sonic SONiC SYSEEPROM syseeprom SYSEEPROMD syseepromd',
)
