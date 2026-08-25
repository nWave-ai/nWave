# Feature: Correct Import Paths in Installed DES Bug Detection
# Bug: Installed DES module uses "from src.des..." imports instead of "from des..."
# Evidence: grep shows real_hook.py contains "from src.des.adapters..."
# Root Cause: Source files copied directly without import path transformation
# Workaround: PYTHONPATH points to project root, masking the bug
# Date: 2026-02-04

Feature: Correct Import Paths in Installed DES
  As a developer
  I want installed DES to use relative imports
  So that it works without PYTHONPATH pointing to development directory

  Background:
    Given the test environment is initialized
    And DES is installed at "~/.claude/lib/python/des"

  # ============================================================================
  # BUG DETECTION SCENARIOS - These tests FAIL with current buggy code
  # When bugs are fixed, these tests will PASS
  # ============================================================================

  @bug-3 @priority-critical
  Scenario: Installed DES should not contain "from src.des" imports
    # Current Behavior (BUG): Files contain imports like:
    #   from src.des.adapters.driven.logging.audit_logger import get_audit_logger
    #   from src.des.ports.driver_ports.hook_port import HookPort
    # Expected Behavior: Imports should be:
    #   from des.adapters.driven.logging.audit_logger import get_audit_logger
    #   from des.ports.driver_ports.hook_port import HookPort

    Given DES is installed at "~/.claude/lib/python/des"
    When I scan all Python files for import statements
    Then no files should contain "from src.des"
    And no files should contain "import src.des"

  @bug-3 @priority-critical
  Scenario: DES should be importable with only installed path in PYTHONPATH
    # Current Behavior (BUG): Import fails with ImportError unless
    # PYTHONPATH includes project root (where src/ exists)
    # Expected Behavior: Import works with only ~/.claude/lib/python in PYTHONPATH

    Given PYTHONPATH contains only "~/.claude/lib/python"
    And PYTHONPATH does NOT contain the development project root
    When I import "from des.application.orchestrator import DESOrchestrator"
    Then the import should succeed without ImportError

  @bug-3 @priority-critical
  Scenario: DES hooks should work with only installed path
    # This is the production scenario - hooks must work without dev directory

    Given PYTHONPATH contains only "~/.claude/lib/python"
    And PYTHONPATH does NOT contain the development project root
    When I execute the DES pre-task hook command
    Then the hook should execute without ImportError
    And the hook should return a valid response

  @bug-3 @priority-critical
  Scenario: All DES submodules should be importable
    # Comprehensive import test spanning every layer of the installed package
    # (domain / application / ports.driver / ports.driven / adapters.driven /
    # adapters.drivers). WTBD-165: the prior list hardcoded three modules that
    # were deleted in b9662eda2 / c8dca89e2 (audit_logger, real_hook, and
    # ports.driver_ports.hook_port — the port moved to ports.driven_ports), so
    # the scenario was permanently @failing for a stale reason. The list below
    # is real current modules (a kept-deliberately-static representative span;
    # full-tree derivation is avoided to keep this regression smoke free of the
    # heavy/optional-dep adapter imports and because the comprehensive
    # "no files contain from src.des" scan scenarios already prove tree-wide
    # import-path correctness). @failing is removed: it now actively passes.

    Given PYTHONPATH contains only "~/.claude/lib/python"
    When I import the following DES modules:
      | module_path                                         |
      | des.domain.error_codes                              |
      | des.application.orchestrator                        |
      | des.application.validator                           |
      | des.application.pre_tool_use_service                |
      | des.application.subagent_stop_service               |
      | des.ports.driver_ports.pre_tool_use_port            |
      | des.ports.driven_ports.hook_port                    |
      | des.adapters.driven.time.system_time                |
      | des.adapters.drivers.hooks.claude_code_hook_adapter |
    Then all imports should succeed without ImportError

  @bug-3 @priority-high
  Scenario: Hook adapter entry point should work standalone
    # The claude_code_hook_adapter.py is the main entry point
    # It must work when invoked as: python3 -m des.adapters.drivers.hooks.claude_code_hook_adapter

    Given PYTHONPATH contains only "~/.claude/lib/python"
    When I run "python3 -m des.adapters.drivers.hooks.claude_code_hook_adapter" without arguments
    Then the command should fail with usage error (missing command)
    And the error should NOT be ImportError

  @bug-3 @priority-high
  Scenario: Verify no src.des references in installed files
    # Detailed scan for all problematic import patterns

    Given DES is installed at "~/.claude/lib/python/des"
    When I scan all Python files in the installed DES directory
    Then I should find 0 occurrences of "from src.des"
    And I should find 0 occurrences of "import src.des"
    And I should find 0 occurrences of "src.des." as a string literal
    And all imports should use "from des." or "import des." patterns

  @bug-3 @priority-medium
  Scenario: Installed DES should have correct package structure
    # Verify the installed package has proper __init__.py files

    Given DES is installed at "~/.claude/lib/python/des"
    Then the following __init__.py files should exist:
      | path                                             |
      | des/__init__.py                                  |
      | des/application/__init__.py                      |
      | des/adapters/__init__.py                         |
      | des/adapters/driven/__init__.py                  |
      | des/adapters/drivers/__init__.py                 |
      | des/ports/__init__.py                            |

  @bug-3 @priority-medium
  Scenario: Import paths should be consistent across all files
    # Cross-file consistency check

    Given DES is installed at "~/.claude/lib/python/des"
    When I analyze import statements across all DES files
    Then all internal imports should use consistent "from des." prefix
    And no mixed "src.des" and "des" prefixes should exist in the same file
