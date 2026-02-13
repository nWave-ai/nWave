"""Test adapters (mocked implementations) for DES ports.

These are test-only mocked implementations for unit and integration testing.
Production code should import from des.adapters.
"""

from tests.des.adapters.in_memory_filesystem import InMemoryFileSystem
from tests.des.adapters.mocked_hook import MockedSubagentStopHook
from tests.des.adapters.mocked_time import MockedTimeProvider
from tests.des.adapters.mocked_validator import MockedTemplateValidator


__all__ = [
    "InMemoryFileSystem",
    "MockedSubagentStopHook",
    "MockedTemplateValidator",
    "MockedTimeProvider",
]
