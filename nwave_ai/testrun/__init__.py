"""Test runs of a project: one queue per account and one selector.

``nwave-ai tests run`` runs a test command through the test queue of the account
(two accounts of one machine have two queues and do not coordinate);
``nwave-ai tests select`` lists the tests a change selects. Both read what the
project declares in the ``tests`` block of its configuration and name no language,
runner or version-control tool themselves.

Layout: ``queue_policy``, ``declaration`` and ``selection`` decide (pure);
``account_queue``, ``capacity``, ``execution``, ``orphan_guard``, ``project_tree``
and ``declaration_source`` act; ``python_dependencies`` is the first dependency
adapter; ``queued_run`` is the entry other code calls; ``cli`` is the command line.
"""
