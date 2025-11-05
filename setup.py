import glob
import os
import os.path as osp
import platform
import shutil
import subprocess
import sys
from itertools import product

import torch
from setuptools import Extension, find_packages, setup
from setuptools.command.build_ext import build_ext
from torch.__config__ import parallel_info
from torch.utils.cpp_extension import CUDA_HOME

__version__ = '2.1.2'
URL = 'https://github.com/rusty1s/pytorch_scatter'

WITH_CUDA = False
if torch.cuda.is_available():
    WITH_CUDA = CUDA_HOME is not None or torch.version.hip
suffices = ['cpu', 'cuda'] if WITH_CUDA else ['cpu']
if os.getenv('FORCE_CUDA', '0') == '1':
    suffices = ['cuda', 'cpu']
    WITH_CUDA = True
if os.getenv('FORCE_ONLY_CUDA', '0') == '1':
    suffices = ['cuda']
    WITH_CUDA = True
if os.getenv('FORCE_ONLY_CPU', '0') == '1':
    suffices = ['cpu']
    WITH_CUDA = False

BUILD_DOCS = os.getenv('BUILD_DOCS', '0') == '1'
WITH_SYMBOLS = os.getenv('WITH_SYMBOLS', '0') == '1'


class CMakeBuild(build_ext):
    """Custom build_ext command that uses CMake to build the extension."""

    def run(self):
        """Build the extension using CMake."""
        if BUILD_DOCS:
            return

        # Get the build directory
        build_temp = osp.abspath(self.build_temp)
        os.makedirs(build_temp, exist_ok=True)

        # Get the package directory where we'll install the library
        extdir = osp.abspath(osp.dirname(self.get_ext_fullpath('torch_scatter')))
        package_dir = osp.join(extdir, 'torch_scatter')
        os.makedirs(package_dir, exist_ok=True)

        # CMake configuration
        cmake_args = [
            f'-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={build_temp}',
            f'-DCMAKE_PREFIX_PATH={torch.utils.cmake_prefix_path}',
            '-DWITH_PYTHON=ON',
        ]

        # Set CUDA flag
        if WITH_CUDA:
            cmake_args.append('-DWITH_CUDA=ON')
        else:
            cmake_args.append('-DWITH_CUDA=OFF')

        # Build configuration
        build_args = ['--config', 'Release']

        # Platform-specific configurations
        if sys.platform == 'win32':
            cmake_args += [
                f'-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_RELEASE={build_temp}',
            ]
            build_args += ['--', '/m']
        else:
            cmake_args += ['-DCMAKE_BUILD_TYPE=Release']
            # Get number of CPUs for parallel build
            import multiprocessing
            num_jobs = multiprocessing.cpu_count()
            build_args += ['--', f'-j{num_jobs}']

        # Run CMake configure
        source_dir = osp.abspath(osp.dirname(__file__))
        subprocess.check_call(['cmake', source_dir] + cmake_args, cwd=build_temp)

        # Run CMake build
        subprocess.check_call(['cmake', '--build', '.'] + build_args, cwd=build_temp)

        # Copy the built library to the package directory
        lib_pattern = 'libtorchscatter.*' if sys.platform != 'win32' else 'torchscatter.dll'
        built_libs = glob.glob(osp.join(build_temp, lib_pattern))

        if not built_libs:
            raise RuntimeError(f'Could not find built library matching {lib_pattern} in {build_temp}')

        for lib in built_libs:
            lib_name = osp.basename(lib)
            dest = osp.join(package_dir, lib_name)
            print(f'Copying {lib} to {dest}')
            shutil.copy(lib, dest)

        # Also install CMake config files to the package
        # Create a cmake subdirectory in the package
        cmake_install_dir = osp.join(package_dir, 'cmake')
        os.makedirs(cmake_install_dir, exist_ok=True)

        # Copy CMake config files
        cmake_files = [
            osp.join(build_temp, 'TorchScatterConfig.cmake'),
            osp.join(build_temp, 'TorchScatterConfigVersion.cmake'),
        ]

        for cmake_file in cmake_files:
            if osp.exists(cmake_file):
                dest = osp.join(cmake_install_dir, osp.basename(cmake_file))
                print(f'Copying {cmake_file} to {dest}')
                shutil.copy(cmake_file, dest)


install_requires = []

test_requires = [
    'pytest',
    'pytest-cov',
]

# work-around hipify abs paths
include_package_data = True
if torch.cuda.is_available() and torch.version.hip:
    include_package_data = False

# Create a dummy extension to trigger the build_ext command
ext_modules = []
if not BUILD_DOCS:
    ext_modules = [Extension('torch_scatter._dummy', sources=[])]

setup(
    name='torch_scatter',
    version=__version__,
    description='PyTorch Extension Library of Optimized Scatter Operations',
    author='Matthias Fey',
    author_email='matthias.fey@tu-dortmund.de',
    url=URL,
    download_url=f'{URL}/archive/{__version__}.tar.gz',
    keywords=['pytorch', 'scatter', 'segment', 'gather'],
    python_requires='>=3.8',
    install_requires=install_requires,
    extras_require={
        'test': test_requires,
    },
    ext_modules=ext_modules,
    cmdclass={
        'build_ext': CMakeBuild,
    },
    packages=find_packages(),
    include_package_data=include_package_data,
    package_data={
        'torch_scatter': ['*.so', '*.dylib', '*.dll', 'cmake/*'],
    },
)
