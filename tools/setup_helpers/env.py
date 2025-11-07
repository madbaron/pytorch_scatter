"""Environment configuration for build."""

import os
import platform
import sys


def check_env_flag(name: str, default: str = "") -> bool:
    """Check if an environment variable is set to a truthy value."""
    return os.getenv(name, default).upper() in ["ON", "1", "YES", "TRUE", "Y"]


def check_negative_env_flag(name: str, default: str = "") -> bool:
    """Check if an environment variable is set to a falsy value."""
    return os.getenv(name, default).upper() in ["OFF", "0", "NO", "FALSE", "N"]


IS_WINDOWS = sys.platform == "win32"
IS_DARWIN = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")
IS_64BIT = sys.maxsize > 2**32

BUILD_DIR = "build"
