"""Bound update-child cleanup even when escaped descendants retain its pipes."""

from __future__ import annotations

import os
import signal
import subprocess

from nwave_ai.platform.update_timing import UPDATE_TIMING


def stop_process(process: subprocess.Popen[str]) -> str:
    """Stop the owned process group and return any unproved termination state.

    A reaped group leader is not proof that every descendant stopped. In
    particular, a descendant can create another session and retain stdout;
    never wait for that pipe's EOF without a deadline or claim it was killed.
    """
    problems: list[str] = []

    try:
        if os.name != "nt":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except ProcessLookupError:
        pass
    except OSError as exc:
        problems.append(f"could not signal the owned process group ({exc})")
    try:
        process.communicate(timeout=UPDATE_TIMING.pipe_drain_seconds)
    except subprocess.TimeoutExpired:
        problems.append(
            "output pipes remained open after the bounded stop; an escaped "
            "descendant may still be running"
        )
    except OSError as exc:
        problems.append(f"could not drain the owned process output ({exc})")
    finally:
        # POSIX communicate uses no reader threads. Closing our read ends does
        # not wait for escaped writers and lets the update lock be released.
        # Windows communicate uses reader threads: closing their buffered file
        # objects can wait on a reader lock, so leave those to process teardown.
        if os.name != "nt":
            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except OSError as exc:
                        problems.append(f"could not close an output pipe ({exc})")
    try:
        process.wait(timeout=UPDATE_TIMING.reap_seconds)
    except subprocess.TimeoutExpired:
        problems.append("the owned process could not be reaped within its bound")
    except OSError as exc:
        problems.append(f"could not reap the owned process ({exc})")
    return "; ".join(problems)
