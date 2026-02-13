"""Ports package for DES hexagonal architecture.

Ports define the interfaces through which the application core communicates
with external systems and infrastructure.

Re-exports all port abstractions from driver and driven port layers for convenience.
"""

from des.ports.driven_ports import (
    ConfigPort,
    FileSystemPort,
    LoggingPort,
    TaskInvocationPort,
    TimeProvider,
)
from des.ports.driver_ports import (
    HookPort,
    ValidatorPort,
)


__all__ = [
    # Driven ports (outbound)
    "ConfigPort",
    "FileSystemPort",
    # Driver ports (inbound)
    "HookPort",
    "LoggingPort",
    "TaskInvocationPort",
    "TimeProvider",
    "ValidatorPort",
]
