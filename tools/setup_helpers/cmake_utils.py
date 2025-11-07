"""CMake utilities."""

from typing import Any


class CMakeValue:
    """Represents a CMake variable value."""
    
    def __init__(self, value: Any, type_: str = "STRING"):
        self.value = value
        self.type = type_
    
    def __str__(self) -> str:
        return str(self.value)


def get_cmake_cache_variables_from_file(f):
    """Parse CMake cache file and return variables as a dictionary."""
    results = {}
    for line in f:
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('//'):
            continue
        
        if '=' in line:
            # Parse line like: VARIABLE_NAME:TYPE=value
            var_part, _, value = line.partition('=')
            if ':' in var_part:
                name, type_ = var_part.split(':', 1)
                results[name] = value
    
    return results
