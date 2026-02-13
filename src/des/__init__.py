"""
DES (Deterministic Execution System) - Post-execution validation and phase tracking.

This package provides deterministic validation hooks that fire when sub-agents complete
execution, ensuring phase progression is tracked accurately and deviations are detected.

Follows hexagonal architecture with:
  - Domain: Core business logic and entities
  - Application: Use cases and orchestration
  - Ports: Abstract interfaces (driver and driven)
  - Adapters: Concrete implementations (drivers and driven)

Core Components:
  - DESOrchestrator: Main DES coordination engine
  - TimeoutMonitor: Domain entity for timeout management
  - ConfigPort: Configuration abstractions
  - HookPort/ValidatorPort: Driver port abstractions
  - TemplateValidator: Driver implementations
  - EnvironmentConfigAdapter/InMemoryConfigAdapter: Driven implementations

For backward compatibility, this module re-exports all key classes and interfaces.
New code should import from the specific layer packages:
  - from des.domain import TimeoutMonitor, TurnCounter
  - from des.application import DESOrchestrator, TemplateValidator
  - from des.ports.driver_ports import HookPort, ValidatorPort
  - from des.ports.driven_ports import ConfigPort, FileSystemPort, TimeProvider
  - from des.adapters.driven import EnvironmentConfigAdapter
"""

# Re-export all key classes for backward compatibility
from des.adapters.driven import (
    ClaudeCodeTaskAdapter,
    EnvironmentConfigAdapter,
    InMemoryConfigAdapter,
    MockedTaskAdapter,
    RealFileSystem,
    SilentLogger,
    StructuredLogger,
    SystemTimeProvider,
)
from des.application.config_loader import ConfigLoader
from des.application.orchestrator import DESOrchestrator, HookPort
from des.application.validator import TDDPhaseValidator, TemplateValidator
from des.domain import (
    InvocationLimitsResult,
    InvocationLimitsValidator,
    TimeoutMonitor,
    TurnCounter,
)
from des.ports.driven_ports import (
    ConfigPort,
    FileSystemPort,
    LoggingPort,
    TaskInvocationPort,
    TimeProvider,
)
from des.ports.driver_ports import ValidatorPort


# Backward compatibility aliases
RealValidator = TemplateValidator
RealFilesystem = RealFileSystem
SystemTime = SystemTimeProvider

__all__ = [
    "ClaudeCodeTaskAdapter",
    "ConfigLoader",
    # Driven ports
    "ConfigPort",
    # Application
    "DESOrchestrator",
    # Driven adapters
    "EnvironmentConfigAdapter",
    "FileSystemPort",
    # Driver ports
    "HookPort",
    "InMemoryConfigAdapter",
    "InvocationLimitsResult",
    "InvocationLimitsValidator",
    "LoggingPort",
    "MockedTaskAdapter",
    "RealFilesystem",
    # Backward compatibility aliases
    "RealValidator",
    "SilentLogger",
    "StructuredLogger",
    "SystemTime",
    "TDDPhaseValidator",
    "TaskInvocationPort",
    "TemplateValidator",
    "TimeProvider",
    # Domain
    "TimeoutMonitor",
    "TurnCounter",
    "ValidatorPort",
]
