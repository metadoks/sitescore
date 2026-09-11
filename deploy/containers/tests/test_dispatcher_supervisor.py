from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

SUPERVISOR_PATH = Path(__file__).parents[1] / "runtime" / "commerce-dispatcher-supervisor.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("faz7_dispatcher_supervisor", SUPERVISOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeStopEvent:
    def __init__(self, stop_after_waits: int | None = None):
        self.waits: list[float] = []
        self.set_called = False
        self.stop_after_waits = stop_after_waits

    def is_set(self) -> bool:
        if self.set_called:
            return True
        return self.stop_after_waits is not None and len(self.waits) >= self.stop_after_waits

    def wait(self, delay: float) -> bool:
        self.waits.append(delay)
        return self.is_set()

    def set(self) -> None:
        self.set_called = True


class _FakeChild:
    def __init__(self, return_code: int):
        self.return_code = return_code
        self.terminated = False

    def wait(self) -> int:
        return self.return_code

    def poll(self):
        return None if not self.terminated else -15

    def terminate(self) -> None:
        self.terminated = True


def test_sup_001_child_command_is_fixed():
    module = _load_module()
    assert module.CHILD_COMMAND == ("sitescore-commerce-dispatch-paid-outbox",)


def test_sup_002_success_resets_failure_backoff(monkeypatch):
    module = _load_module()
    event = _FakeStopEvent(stop_after_waits=3)
    return_codes = iter([1, 0, 1])
    monkeypatch.setattr(module, "_stop_event", event)
    monkeypatch.setattr(module, "_install_signal_handlers", lambda: None)
    monkeypatch.setattr(module.subprocess, "Popen", lambda command: _FakeChild(next(return_codes)))

    assert module.run() == 0
    assert event.waits == [2.0, 2.0, 2.0]


def test_sup_003_failure_backoff_is_bounded(monkeypatch):
    module = _load_module()
    event = _FakeStopEvent(stop_after_waits=6)
    monkeypatch.setattr(module, "_stop_event", event)
    monkeypatch.setattr(module, "_install_signal_handlers", lambda: None)
    monkeypatch.setattr(module.subprocess, "Popen", lambda command: _FakeChild(7))

    assert module.run() == 0
    assert event.waits == [2.0, 4.0, 8.0, 16.0, 30.0, 30.0]
    assert max(event.waits) == module.FAILURE_BACKOFF_MAX_SECONDS


def test_sup_004_success_and_failure_paths_never_busy_loop(monkeypatch):
    module = _load_module()
    event = _FakeStopEvent(stop_after_waits=4)
    return_codes = iter([0, 4, 0, 9])
    monkeypatch.setattr(module, "_stop_event", event)
    monkeypatch.setattr(module, "_install_signal_handlers", lambda: None)
    monkeypatch.setattr(module.subprocess, "Popen", lambda command: _FakeChild(next(return_codes)))

    assert module.run() == 0
    assert len(event.waits) == 4
    assert all(delay > 0 for delay in event.waits)


def test_sup_005_sigterm_sigint_stop_and_terminate_child():
    module = _load_module()
    event = _FakeStopEvent()
    child = _FakeChild(0)
    module._stop_event = event
    module._child = child

    module._handle_signal(15, None)
    assert event.set_called is True
    assert child.terminated is True


def test_sup_006_no_business_package_import_or_business_call():
    source = SUPERVISOR_PATH.read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(not alias.name.startswith("sitescore_commerce") for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith("sitescore_commerce")
    assert "sitescore_commerce" not in source
    assert "dispatch_once" not in source
    assert "mark_published" not in source
    assert "stdout=" not in source
    assert "capture_output" not in source


def test_sup_007_no_environment_dump_or_secret_logging():
    source = SUPERVISOR_PATH.read_text()
    assert "os.environ" not in source
    assert "environ" not in source
    assert "env=" not in source
    assert "SECRET" not in source
    assert "TOKEN" not in source
    assert "PASSWORD" not in source
