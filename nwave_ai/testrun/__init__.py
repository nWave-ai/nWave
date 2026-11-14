"""Test runs of a project: one queue per account and one selector.

``nwave-ai tests run`` runs a test command through the test queue of the account
(two accounts of one machine have two queues and do not coordinate);
``nwave-ai tests select`` lists the tests a change selects. Both read what the
project declares in the ``tests`` block of its configuration and name no language,
runner or version-control tool themselves.

Layout: ``queue_policy``, ``declaration``, ``selection``, ``dependents`` and the
closure of ``dependents`` decide (pure); ``account_queue``, ``capacity``, ``execution``,
``orphan_guard``, ``project_tree``, ``dependents.command`` and ``declaration_source``
act; ``project_selection`` wires them for every caller; ``queued_run`` is the entry
other code calls; ``cli`` is the command line. The language rules of a repository are
its own declared command (for nWave: ``scripts/hooks/python_dependents.py``).
"""
