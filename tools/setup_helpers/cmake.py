"""Manages CMake build process."""

import multiprocessing
import os
import shutil
import sys
from pathlib import Path
from subprocess import CalledProcessError, check_call
from typing import Any, Dict, Optional

from .cmake_utils import get_cmake_cache_variables_from_file
from .env import BUILD_DIR, IS_WINDOWS, IS_64BIT, get_cuda_env_flags


def _mkdir_p(d: str) -> None:
    """Create directory recursively."""
    try:
        os.makedirs(d, exist_ok=True)
    except OSError as e:
        raise RuntimeError(
            f"Failed to create folder {os.path.abspath(d)}: {e.strerror}"
        ) from e


# Determine if we should use Ninja
USE_NINJA = bool(shutil.which("ninja") and os.getenv("USE_NINJA", "1") != "0")
if "CMAKE_GENERATOR" in os.environ:
    USE_NINJA = os.environ["CMAKE_GENERATOR"].lower() == "ninja"


class CMake:
    """Manages cmake build process."""

    def __init__(self, build_dir: str = BUILD_DIR) -> None:
        self._cmake_command = "cmake"
        self.build_dir = build_dir

    @property
    def _cmake_cache_file(self) -> str:
        """Returns the path to CMakeCache.txt."""
        return os.path.join(self.build_dir, "CMakeCache.txt")

    def get_cmake_cache_variables(self) -> Dict[str, Any]:
        """Get the CMake cache variables from CMakeCache.txt."""
        with open(self._cmake_cache_file) as f:
            return get_cmake_cache_variables_from_file(f)

    def generate(
        self,
        version: Optional[str],
        build_python: bool,
        build_dir: Optional[str] = None,
        cmake_prefix_path: Optional[str] = None,
        extra_cmake_args: Optional[list] = None,
        source_dir: Optional[str] = None,
    ) -> None:
        """Runs cmake to generate native build files."""
        
        if build_dir:
            self.build_dir = build_dir
        
        _mkdir_p(self.build_dir)

        args = [self._cmake_command]
        
        # Set generator
        if USE_NINJA:
            os.environ["CMAKE_GENERATOR"] = "Ninja"
            args.append("-GNinja")
        elif IS_WINDOWS:
            generator = os.getenv("CMAKE_GENERATOR", "Visual Studio 16 2019")
            args.append("-G" + generator)
            if IS_64BIT:
                args.append("-Ax64")

        # Add source directory
        if source_dir is None:
            # Default to repository root (two levels up from this file)
            source_dir = str(Path(__file__).absolute().parents[2])
        args.append(source_dir)
        
        # Set build type
        build_type = "Release"
        if os.getenv("DEBUG", "0") == "1":
            build_type = "Debug"
        elif os.getenv("REL_WITH_DEB_INFO", "0") == "1":
            build_type = "RelWithDebInfo"
        args.append(f"-DCMAKE_BUILD_TYPE={build_type}")
        
        # Set install prefix to torch_scatter directory
        install_dir = os.path.join(source_dir, "torch_scatter")
        args.append(f"-DCMAKE_INSTALL_PREFIX={install_dir}")
        
        # Build options
        args.append(f"-DWITH_PYTHON={'ON' if build_python else 'OFF'}")
        
        # CUDA support
        with_cuda = get_cuda_env_flags()
        args.append(f"-DWITH_CUDA={'ON' if with_cuda else 'OFF'}")
        
        # Set CMake prefix path if provided
        if cmake_prefix_path:
            args.append(f"-DCMAKE_PREFIX_PATH={cmake_prefix_path}")
        
        # Add version
        if version:
            args.append(f"-DTORCHSCATTER_VERSION={version}")
        
        # Add any extra cmake args
        if extra_cmake_args:
            args.extend(extra_cmake_args)
        
        # Run cmake
        print(f"Running CMake with args: {' '.join(args)}")
        try:
            check_call(args, cwd=self.build_dir)
        except CalledProcessError as e:
            raise RuntimeError(f"Failed to run CMake: {e}") from e

    def build(self, parallel: bool = True) -> None:
        """Build the project using cmake --build."""
        
        args = [self._cmake_command, "--build", "."]
        
        if parallel:
            max_jobs = os.getenv("MAX_JOBS", str(multiprocessing.cpu_count()))
            if USE_NINJA:
                args.extend(["-j", max_jobs])
            elif IS_WINDOWS:
                args.extend(["--", f"/maxcpucount:{max_jobs}"])
            else:
                args.extend(["--", "-j", max_jobs])
        
        args.append("--config")
        if os.getenv("DEBUG", "0") == "1":
            args.append("Debug")
        elif os.getenv("REL_WITH_DEB_INFO", "0") == "1":
            args.append("RelWithDebInfo")
        else:
            args.append("Release")
        
        print(f"Building with CMake: {' '.join(args)}")
        try:
            check_call(args, cwd=self.build_dir)
        except CalledProcessError as e:
            raise RuntimeError(f"Failed to build with CMake: {e}") from e

    def install(self) -> None:
        """Install the built libraries."""
        
        args = [self._cmake_command, "--install", "."]
        
        args.append("--config")
        if os.getenv("DEBUG", "0") == "1":
            args.append("Debug")
        elif os.getenv("REL_WITH_DEB_INFO", "0") == "1":
            args.append("RelWithDebInfo")
        else:
            args.append("Release")
        
        print(f"Installing with CMake: {' '.join(args)}")
        try:
            check_call(args, cwd=self.build_dir)
        except CalledProcessError as e:
            raise RuntimeError(f"Failed to install with CMake: {e}") from e
