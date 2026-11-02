"""Bounded child-process spawn with process-group reaping.

Declared copy (decision 14) of the reaped-spawn closure, with three edits forced
by the repository rules. It imports only the standard library.

Edits against the source: ``default_timeout_seconds`` reads the run ceiling itself
instead of importing a test-execution module; ``spawn`` and ``_run_reaped`` pass
``stdin`` explicitly, so ``tests/build/test_no_unbounded_unstdin_spawn.py`` finds no
unstated descriptor.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import threading
import time
from typing import Any


_active_process_groups: set[int] = set()
_active_process_groups_lock = threading.Lock()


def _register_active_process_group(pgid: int) -> None:
    with _active_process_groups_lock:
        _active_process_groups.add(pgid)


def _forget_active_process_group(pgid: int) -> None:
    with _active_process_groups_lock:
        _active_process_groups.discard(pgid)


def default_timeout_seconds() -> float:
    """The bound applied when a caller names no tier of its own.

    The RUN ceiling: ``NWAVE_GATE_RUN_TIMEOUT`` when set to a number, 2700 seconds
    otherwise. Rationale (RCA §8): an omitted bound must become a ceiling that catches
    an infinite hang, not one that false-kills a legitimate long child. Callers with a
    shorter tier pass their own ``timeout=``.
    """
    try:
        return float(os.environ.get("NWAVE_GATE_RUN_TIMEOUT", "2700"))
    except ValueError:
        return 2700.0


class SpawnTimeout(subprocess.TimeoutExpired):
    """A fired wall-clock bound that explains itself.

    Subclasses ``subprocess.TimeoutExpired`` deliberately: every existing
    ``except subprocess.TimeoutExpired`` handler in the tree keeps working
    unchanged, so routing a site through the boundary cannot silently break its
    timeout handling. What is added is a ``__str__`` carrying WHAT / WHY / HOW --
    a bare ``TimeoutExpired`` carries what and why but no HOW, leaving the
    operator a number and no lever.
    """

    def __init__(
        self,
        cmd: Any,
        timeout: float,
        *,
        output: Any = None,
        stderr: Any = None,
        timeout_env: str | None = None,
    ) -> None:
        super().__init__(cmd, timeout, output=output, stderr=stderr)
        self.timeout_env = timeout_env

    @property
    def captured_text(self) -> str:
        """Whatever the killed child managed to emit, as text.

        ``TimeoutExpired.stdout`` is ``str | bytes | None`` depending on the
        spawn's capture mode; a caller reporting to an operator wants one type.
        The partial output is the evidence of WHERE the child got stuck, so it is
        normalised here rather than discarded at each call site.
        """
        captured = self.stdout
        if isinstance(captured, bytes):
            return captured.decode(errors="replace")
        return captured or ""

    def _how(self) -> str:
        if self.timeout_env:
            return (
                f"if the child was still doing real work, raise its bound with "
                f"{self.timeout_env}=<seconds> and re-run; if it was genuinely "
                f"stuck, the captured output on this exception is the evidence."
            )
        return (
            "if the child was still doing real work, pass a larger `timeout=` at "
            "the call site; if it was genuinely stuck, the captured output on this "
            "exception is the evidence."
        )

    def __str__(self) -> str:
        return (
            f"WHAT: the child process timed out -- {_describe(self.cmd)} did not "
            f"finish within its {self.timeout:g}s wall-clock bound and was killed "
            f"together with its whole process group.\n"
            f"WHY: it was still running when the bound fired. Either it is "
            f"genuinely stuck (a child blocked on a descriptor nobody will ever "
            f"write to or close -- the deadlock class this boundary exists to "
            f"bound), or the work legitimately needs longer than this tier allows.\n"
            f"HOW: {self._how()}"
        )


class SpawnQuiescenceError(subprocess.SubprocessError):
    """An owned native process group has not been observed to exit."""

    def __init__(self, pid: int, stdout: Any, stderr: Any):
        super().__init__(
            f"process group {pid} remains present or unobservable after termination; "
            "establish that its writers stopped before reusing the workspace"
        )
        self.stdout = stdout
        self.stderr = stderr


def _require_process_group_exit(pid: int, stdout: Any, stderr: Any) -> None:
    # Signal delivery and orphan reaping are asynchronous. A present group
    # is not an exit witness; give the kernel a bounded chance to reap it.
    deadline = time.monotonic() + 1.0
    while True:
        try:
            os.killpg(pid, 0)
        except ProcessLookupError:
            return
        except OSError:
            raise SpawnQuiescenceError(pid, stdout, stderr) from None
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise SpawnQuiescenceError(pid, stdout, stderr)
        time.sleep(min(0.01, remaining))


def spawn(
    argv: Any,
    *,
    timeout: float | None = None,
    timeout_env: str | None = None,
    reap_process_group: bool = False,
    quiesce_process_group: bool = False,
    **subprocess_kwargs: Any,
) -> subprocess.CompletedProcess[Any]:
    """Run a child process with an explicit stdin and an explicit bound.

    Drop-in for ``subprocess.run``: ``argv`` and every ``**subprocess_kwargs``
    (``cwd``, ``env``, ``shell``, ``capture_output``, ``text``, ``check``,
    ``input``, ``stdin``, ``stdout``, ``stderr``, ...) mean exactly what they mean
    there, the execution is ``subprocess.run``'s, and the return value is a plain
    ``CompletedProcess``. ONE default is INJECTED and never imposed over a
    caller's choice: ``stdin=subprocess.DEVNULL`` when the caller passed neither
    ``stdin=`` nor ``input=``.

    ``timeout=None`` means "no tier named" and resolves to
    ``default_timeout_seconds()`` -- omission can no longer mean unbounded.
    ``timeout_env`` names the operator's override for the tier in play and is
    quoted in the HOW of a fired bound.

    ``reap_process_group`` is the PER-TIER opt-in for process-group reaping; it is
    deliberately not a blanket default, because a new session detaches the child
    from the terminal's foreground process group.

    ``quiesce_process_group`` also requests group cleanup after normal exit,
    for callers about to release mutable shared resources. It does not confine
    daemons which deliberately escape the process group.

    Raises ``SpawnTimeout`` (a ``subprocess.TimeoutExpired``) when the bound
    fires.
    """
    bound = default_timeout_seconds() if timeout is None else timeout
    if "stdin" not in subprocess_kwargs and "input" not in subprocess_kwargs:
        subprocess_kwargs["stdin"] = subprocess.DEVNULL

    try:
        if reap_process_group or quiesce_process_group:
            return _run_reaped(
                argv,
                timeout=bound,
                quiesce_process_group=quiesce_process_group,
                **subprocess_kwargs,
            )
        stdin = subprocess_kwargs.pop("stdin", None)
        return subprocess.run(argv, timeout=bound, stdin=stdin, **subprocess_kwargs)
    except subprocess.TimeoutExpired as expired:
        raise SpawnTimeout(
            argv,
            bound,
            output=expired.stdout,
            stderr=expired.stderr,
            timeout_env=timeout_env,
        ) from None


def _run_reaped(
    argv: Any,
    *,
    timeout: float,
    quiesce_process_group: bool = False,
    **subprocess_kwargs: Any,
) -> subprocess.CompletedProcess[Any]:
    """``subprocess.run`` semantics, plus a process-group reap on the bound.

    Hand-rolled around ``Popen`` because ``subprocess.run`` cannot serve this
    duty: it exposes no handle on the child, and on POSIX its timeout path is
    ``kill()`` + ``wait()`` on the DIRECT child only (measured, RCA §8) -- the
    grandchildren survive. Owning the ``Popen`` is what makes the child's pid, and
    therefore its process group, knowable.

    ``capture_output`` / ``input`` / ``check`` are translated exactly as
    ``subprocess.run`` translates them, so a caller sees no semantic difference
    between the two engines beyond the reap itself.
    """
    stdin_input = subprocess_kwargs.pop("input", None)
    check = bool(subprocess_kwargs.pop("check", False))

    if stdin_input is not None:
        if "stdin" in subprocess_kwargs:
            raise ValueError("stdin and input arguments may not both be used.")
        subprocess_kwargs["stdin"] = subprocess.PIPE

    stdin = subprocess_kwargs.pop("stdin", None)

    if subprocess_kwargs.pop("capture_output", False):
        if "stdout" in subprocess_kwargs or "stderr" in subprocess_kwargs:
            raise ValueError(
                "stdout and stderr arguments may not be used with capture_output."
            )
        subprocess_kwargs["stdout"] = subprocess.PIPE
        subprocess_kwargs["stderr"] = subprocess.PIPE

    subprocess_kwargs["start_new_session"] = True

    with subprocess.Popen(argv, stdin=stdin, **subprocess_kwargs) as child:
        # Published for the lifetime of the Popen so a process-wide signal
        # handler can reach this group from outside this call frame.
        _register_active_process_group(child.pid)
        stdout = stderr = None
        try:
            try:
                stdout, stderr = child.communicate(stdin_input, timeout=timeout)
            except subprocess.TimeoutExpired:
                stdout, stderr = _reap_and_drain(child)
                raise subprocess.TimeoutExpired(
                    argv, timeout, output=stdout, stderr=stderr
                ) from None
            except BaseException:
                # An abnormal exit (Ctrl-C, a signal) would otherwise leave the
                # whole group orphaned: the new session detached it from the
                # terminal's foreground group, so nothing else will ever signal
                # it.
                _reap_and_drain(child)
                raise
        finally:
            if quiesce_process_group:
                _reap_process_group(child.pid)
            _forget_active_process_group(child.pid)
            if quiesce_process_group:
                _require_process_group_exit(child.pid, stdout, stderr)

    completed = subprocess.CompletedProcess(argv, child.returncode, stdout, stderr)
    if check:
        completed.check_returncode()
    return completed


def _reap_and_drain(child: subprocess.Popen[Any]) -> tuple[Any, Any]:
    """SIGKILL the child's process group, then collect whatever it produced.

    Order matters: draining FIRST would block until every holder of the capture
    pipe closed it, and a surviving grandchild holding that pipe open is the very
    deadlock under repair. Once the group is dead the second ``communicate`` -- the
    retry shape the stdlib documents for ``TimeoutExpired`` -- returns at once.
    """
    _reap_process_group(child.pid)
    with contextlib.suppress(ValueError, OSError):
        return child.communicate()
    return None, None


def _reap_process_group(pid: int) -> None:
    """SIGKILL the whole process group led by ``pid`` (best-effort, idempotent).

    ``pid`` is the group leader (``_run_reaped`` spawns with
    ``start_new_session=True``, so its pgid == its pid) and every descendant that
    did not itself call ``setsid`` keeps that pgid. ``ProcessLookupError`` (the
    group is already empty) is the success case.
    """
    with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
        os.killpg(pid, signal.SIGKILL)


def _describe(cmd: Any) -> str:
    """Render a spawn's command for an operator-facing message."""
    if isinstance(cmd, (list, tuple)):
        return " ".join(str(part) for part in cmd)
    return str(cmd)
