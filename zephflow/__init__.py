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

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("zephflow")
except PackageNotFoundError:
    __version__ = "unknown"

from . import core, jar_manager
from .core import ZephFlow, start_flow
from .jar_manager import JarManager

__all__ = ["ZephFlow", "start_flow", "JarManager", "__version__"]

# Clean up namespace
del core, jar_manager
