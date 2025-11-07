import os
import os.path as osp
import shutil
import sys
from pathlib import Path

import torch
from setuptools import find_packages, setup
from setuptools.command.build_ext import build_ext

# Import cmake build helper
from tools.setup_helpers.cmake import CMake

__version__ = '2.1.2'
URL = 'https://github.com/rusty1s/pytorch_scatter'

BUILD_DOCS = os.getenv('BUILD_DOCS', '0') == '1'


class CMakeBuild(build_ext):
    """Custom build_ext command that uses CMake."""
    
    def run(self):
        """Run CMake build process."""
        if BUILD_DOCS:
            # Skip building for docs
            return
        
        try:
            # Get PyTorch cmake prefix path
            import torch.utils.cpp_extension
            torch_dir = Path(torch.__file__).parent
            cmake_prefix_path = str(torch_dir / 'share' / 'cmake')
            
            # Fallback to torch directory if share/cmake doesn't exist
            if not os.path.exists(cmake_prefix_path):
                cmake_prefix_path = str(torch_dir)
            
            # Initialize CMake
            cmake = CMake()
            
            # Generate build files
            print("Configuring CMake build...")
            cmake.generate(
                version=__version__,
                build_python=True,
                cmake_prefix_path=cmake_prefix_path,
            )
            
            # Build the project
            print("Building with CMake...")
            cmake.build(parallel=True)
            
            # Install to torch_scatter directory
            print("Installing libraries...")
            cmake.install()
            
            # Copy built libraries to the build/lib directory for development installs
            if self.build_lib:
                src_dir = Path('torch_scatter')
                dst_dir = Path(self.build_lib) / 'torch_scatter'
                dst_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy .so files
                for so_file in src_dir.glob('*.so'):
                    shutil.copy2(so_file, dst_dir / so_file.name)
                    print(f"Copied {so_file} to {dst_dir / so_file.name}")
                
                # Copy share directory (CMake configs)
                if (src_dir / 'share').exists():
                    shutil.copytree(src_dir / 'share', dst_dir / 'share', dirs_exist_ok=True)
                    print(f"Copied share directory to {dst_dir / 'share'}")
                
                # Copy include directory (headers)
                if (src_dir / 'include').exists():
                    shutil.copytree(src_dir / 'include', dst_dir / 'include', dirs_exist_ok=True)
                    print(f"Copied include directory to {dst_dir / 'include'}")
            
        except Exception as e:
            raise RuntimeError(f"CMake build failed: {e}") from e
    
    def get_outputs(self):
        """Return list of built files."""
        # Return empty list since CMake handles the installation
        return []


install_requires = []

test_requires = [
    'pytest',
    'pytest-cov',
]

# work-around hipify abs paths
include_package_data = True
if torch.cuda.is_available() and torch.version.hip:
    include_package_data = False

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
    ext_modules=[],  # CMake handles the extensions
    cmdclass={
        'build_ext': CMakeBuild,
    },
    packages=find_packages(),
    include_package_data=include_package_data,
)
