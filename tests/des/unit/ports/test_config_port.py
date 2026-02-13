"""
Unit tests for ConfigPort and its adapters.

Tests validate that ConfigPort interface is correctly defined and that
EnvironmentConfigAdapter and InMemoryConfigAdapter implement the interface correctly.
"""

import os


def test_config_port_interface_defines_required_methods():
    """
    Test that ConfigPort interface defines all required abstract methods.

    Given: ConfigPort interface
    When: Interface is inspected
    Then: All required methods are defined as abstract
    """
    # Verify it's an abstract base class
    from abc import ABC

    from des.ports.driven_ports.config_port import ConfigPort

    assert issubclass(ConfigPort, ABC)

    # Verify required methods exist
    assert hasattr(ConfigPort, "get_max_turns_default")
    assert hasattr(ConfigPort, "get_timeout_threshold_default")


def test_in_memory_config_adapter_returns_hardcoded_values():
    """
    Test that InMemoryConfigAdapter returns expected hardcoded test values.

    Given: InMemoryConfigAdapter instance
    When: Configuration methods are called
    Then: Hardcoded test values are returned
    """
    from des.adapters.driven.config.in_memory_config_adapter import (
        InMemoryConfigAdapter,
    )

    config = InMemoryConfigAdapter()

    # Get default values
    max_turns = config.get_max_turns_default()
    timeout_threshold = config.get_timeout_threshold_default()

    # Verify values are integers and reasonable for testing
    assert isinstance(max_turns, int)
    assert isinstance(timeout_threshold, int)
    assert max_turns == 10  # Expected test default
    assert timeout_threshold == 300  # Expected test default (5 minutes)


def test_in_memory_config_adapter_accepts_custom_values():
    """
    Test that InMemoryConfigAdapter accepts custom values at initialization.

    Given: InMemoryConfigAdapter with custom values
    When: Configuration methods are called
    Then: Custom values are returned
    """
    from des.adapters.driven.config.in_memory_config_adapter import (
        InMemoryConfigAdapter,
    )

    config = InMemoryConfigAdapter(max_turns=5, timeout_threshold=60)

    assert config.get_max_turns_default() == 5
    assert config.get_timeout_threshold_default() == 60


def test_environment_config_adapter_reads_env_variables():
    """
    Test that EnvironmentConfigAdapter reads from environment variables.

    Given: Environment variables are set
    When: Configuration methods are called
    Then: Values from environment are returned
    """
    from des.adapters.driven.config.environment_config_adapter import (
        EnvironmentConfigAdapter,
    )

    # Set environment variables
    os.environ["DES_MAX_TURNS_DEFAULT"] = "15"
    os.environ["DES_TIMEOUT_THRESHOLD_DEFAULT"] = "600"

    try:
        config = EnvironmentConfigAdapter()

        # Verify values are read from environment
        assert config.get_max_turns_default() == 15
        assert config.get_timeout_threshold_default() == 600
    finally:
        # Clean up environment
        os.environ.pop("DES_MAX_TURNS_DEFAULT", None)
        os.environ.pop("DES_TIMEOUT_THRESHOLD_DEFAULT", None)


def test_environment_config_adapter_uses_defaults_when_env_not_set():
    """
    Test that EnvironmentConfigAdapter uses sensible defaults when env vars not set.

    Given: No environment variables set
    When: Configuration methods are called
    Then: Default values are returned
    """
    from des.adapters.driven.config.environment_config_adapter import (
        EnvironmentConfigAdapter,
    )

    # Ensure env vars are not set
    os.environ.pop("DES_MAX_TURNS_DEFAULT", None)
    os.environ.pop("DES_TIMEOUT_THRESHOLD_DEFAULT", None)

    config = EnvironmentConfigAdapter()

    # Verify defaults are returned
    max_turns = config.get_max_turns_default()
    timeout_threshold = config.get_timeout_threshold_default()

    assert isinstance(max_turns, int)
    assert isinstance(timeout_threshold, int)
    assert max_turns > 0
    assert timeout_threshold > 0


def test_in_memory_config_adapter_implements_config_port():
    """
    Test that InMemoryConfigAdapter implements ConfigPort interface.

    Given: InMemoryConfigAdapter class
    When: Class is inspected
    Then: It is an instance of ConfigPort
    """
    from des.adapters.driven.config.in_memory_config_adapter import (
        InMemoryConfigAdapter,
    )
    from des.ports.driven_ports.config_port import ConfigPort

    config = InMemoryConfigAdapter()
    assert isinstance(config, ConfigPort)


def test_environment_config_adapter_implements_config_port():
    """
    Test that EnvironmentConfigAdapter implements ConfigPort interface.

    Given: EnvironmentConfigAdapter class
    When: Class is inspected
    Then: It is an instance of ConfigPort
    """
    from des.adapters.driven.config.environment_config_adapter import (
        EnvironmentConfigAdapter,
    )
    from des.ports.driven_ports.config_port import ConfigPort

    config = EnvironmentConfigAdapter()
    assert isinstance(config, ConfigPort)
