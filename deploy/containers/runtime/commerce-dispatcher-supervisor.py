#!/usr/bin/env python3
from __future__ import annotations

import signal
import subprocess
import sys
import threading

CHILD_COMMAND = ("sitescore-commerce-dispatch-paid-outbox",)
SUCCESS_DELAY_SECONDS = 2.0
FAILURE_BACKOFF_INITIAL_SECONDS = 2.0
FAILURE_BACKOFF_MAX_SECONDS = 30.0

_stop_event = threading.Event()
_child: subprocess.Popen[bytes] | None = None


def _log(message: str) -> None:
    print(f"dispatcher-supervisor: {message}", file=sys.stderr, flush=True)


def _handle_signal(signum: int, _frame: object) -> None:
    global _child
    _log(f"received signal={signum}; stopping")
    _stop_event.set()
    child = _child
    if child is not None and child.poll() is None:
        child.terminate()


def _install_signal_handlers() -> None:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)


def run() -> int:
    global _child
    backoff = FAILURE_BACKOFF_INITIAL_SECONDS
    _install_signal_handlers()

    while not _stop_event.is_set():
        _log("starting frozen one-shot dispatcher")
        _child = subprocess.Popen(CHILD_COMMAND)
        return_code = _child.wait()
        _child = None

        if _stop_event.is_set():
            break

        if return_code == 0:
            backoff = FAILURE_BACKOFF_INITIAL_SECONDS
            delay = SUCCESS_DELAY_SECONDS
            _log(f"child exit_code=0; sleep_seconds={delay:g}")
        else:
            delay = backoff
            _log(f"child exit_code={return_code}; backoff_seconds={delay:g}")
            backoff = min(FAILURE_BACKOFF_MAX_SECONDS, backoff * 2.0)

        _stop_event.wait(delay)

    _log("stopped")
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
