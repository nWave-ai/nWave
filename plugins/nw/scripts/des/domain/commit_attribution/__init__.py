"""Commit-attribution domain — pure command→command trailer rewrite.

Productionizes the SPIKE Part-A mechanism (`spike/inject_trailer.py`) plus the
new compound-command handling (ADR-CA-006 D2). Pure functions only: no I/O, no
adapter imports (hexagonal purity, F-D-09). The application service orchestrates;
the adapter translates the hook protocol.
"""
