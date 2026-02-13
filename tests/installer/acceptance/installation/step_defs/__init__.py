"""
Step definitions for installation acceptance tests.

CRITICAL: Hexagonal boundary enforcement - tests invoke CLI entry points ONLY.
- FORBIDDEN: Direct imports of internal components
- REQUIRED: Invoke through driving ports (scripts/install/*.py)
"""
