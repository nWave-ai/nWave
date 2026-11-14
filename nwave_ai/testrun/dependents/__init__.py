"""Which files depend on a file: the edges, their closure and the command that answers.

``edge`` holds one dependency; ``closure`` follows edges as a pure fold; ``declared``
and ``command`` are the project's declaration of the command and the process that runs
it. The tool names no language here: the answer comes from the command the project
declares.
"""
