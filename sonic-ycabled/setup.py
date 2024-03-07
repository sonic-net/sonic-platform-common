from setuptools import setup, find_packages
from setuptools.command.build_py import build_py as _build_py
import distutils.command
import os.path
import sys

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

class BuildPyCommand(_build_py, object):

    # When 'python3 -m build -n' is executed, by default 'sdist' command
    # is executed and it copies .py and other default files to separate
    # dir and generates a sdist of it, from which a wheel is created.
    # Hence, generate the required python files in initialization of
    # 'build_py' itself to make it available for other commands.
    def initialize_options(self):
        # .proto files are not copied by 'sdist' command.
        # So, execute GrpcTool only if the proto dir is present.
        if os.path.exists('proto'):
            self.run_command('GrpcTool')

        proto_py_files = ['proto_out/linkmgr_grpc_driver_pb2.py', 'proto_out/linkmgr_grpc_driver_pb2_grpc.py']
        for py_file in proto_py_files:
            if not os.path.exists(py_file):
                print('Required file not present: {0}'.format(py_file))
                sys.exit(1)

        super(BuildPyCommand, self).initialize_options()

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
    cmdclass={
        'build_py': BuildPyCommand,
        'GrpcTool': GrpcTool
    },
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
