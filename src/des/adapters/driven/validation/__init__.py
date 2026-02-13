"""
Validation adapters for DES (driven side).

This module contains adapters that interact with external systems
for validation purposes (e.g., git subprocess for scope validation).
"""

from des.adapters.driven.validation.git_scope_checker import GitScopeChecker
from des.ports.driven_ports.scope_checker import ScopeCheckResult


__all__ = ["GitScopeChecker", "ScopeCheckResult"]
