"""
ZephFlow Python SDK

A Python client library for building and executing ZephFlow data
processing pipelines.

Example:
    >>> import zephflow
    >>> flow = zephflow.ZephFlow.start_flow()
    >>> flow = flow.filter("$.value > 10").stdout_sink("JSON_OBJECT")
    >>> flow.execute("job-1", "dev", "my-service")
"""

from . import core, jar_manager
from .core import ZephFlow, start_flow
from .jar_manager import JarManager
from .versions import JAVA_SDK_VERSION, PYTHON_SDK_VERSION

# Use versions.py as the source of truth
__version__ = PYTHON_SDK_VERSION

__all__ = ["ZephFlow", "start_flow", "JarManager", "__version__", "JAVA_SDK_VERSION"]

# Clean up namespace
del core, jar_manager
