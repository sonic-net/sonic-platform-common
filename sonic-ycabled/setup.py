from setuptools import setup, find_packages
from distutils.command.build_ext import build_ext as _build_ext
import distutils.command

class GrpcTool(distutils.cmd.Command):
    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import grpc_tools.protoc

        grpc_tools.protoc.main([
            'grpc_tools.protoc',
            '-Iproto',
            '--python_out=.',
            '--grpc_python_out=.',
            'proto/proto_out/linkmgr_grpc_driver.proto'
        ])

class BuildExtCommand (_build_ext, object):
    def run(self):
        self.run_command('GrpcTool')
        super(BuildExtCommand, self).run()

setup(
    name='sonic-ycabled',
    version='1.0',
    description='Y-cable and smart nic configuration daemon for SONiC',
    license='Apache 2.0',
    author='SONiC Team',
    author_email='linuxnetdev@microsoft.com',
    url='https://github.com/Azure/sonic-platform-daemons',
    maintainer='Vaibhav Dahiya',
    maintainer_email='vdahiya@microsoft.com',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'ycabled = ycable.ycable:main',
        ]
    },
    cmdclass={'build_ext': BuildExtCommand,
              'GrpcTool': GrpcTool},
    install_requires=[
        # NOTE: This package also requires swsscommon, but it is not currently installed as a wheel
        'enum34; python_version < "3.4"',
        'sonic-py-common',
    ],
    setup_requires=[
        'wheel',
        'grpcio-tools'
    ],
    tests_require=[
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
        'Programming Language :: Python :: 3.7',
        'Topic :: System :: Hardware',
    ],
    keywords='sonic SONiC TRANSCEIVER transceiver daemon YCABLE ycable',
)
