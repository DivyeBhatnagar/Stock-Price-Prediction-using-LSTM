"""
conftest.py — Shared pytest fixtures for backend tests
"""

import asyncio
import sys
import os
import types
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# ── Stub out heavy / unavailable third-party modules ─────────────────────────

def _ensure_stub(name: str) -> types.ModuleType:
    """Create an empty stub module if it isn't already in sys.modules."""
    if name not in sys.modules:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    return sys.modules[name]

# Build the entire apscheduler stub hierarchy
for _name in [
    "apscheduler",
    "apscheduler.schedulers",
    "apscheduler.schedulers.background",
    "apscheduler.triggers",
    "apscheduler.triggers.cron",
    "apscheduler.triggers.interval",
    "tensorflow",
    "keras",
]:
    _ensure_stub(_name)

# Give the sub-modules the names that scheduler.py does `from X import Y` on
sys.modules["apscheduler.schedulers.background"].BackgroundScheduler = MagicMock
sys.modules["apscheduler.triggers.cron"].CronTrigger                 = MagicMock
sys.modules["apscheduler.triggers.interval"].IntervalTrigger         = MagicMock


@pytest.fixture(scope="session")
def event_loop():
    """Provide a single event loop for the entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client(monkeypatch):
    """
    Return a synchronous FastAPI TestClient.
    Patches the data scheduler and live publisher so they don't
    attempt real I/O during unit tests.
    """
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    class _FakeSched:
        manager = None
        def start(self): pass
        def stop(self):  pass
        def get_status(self): return {}
        def get_history(self, *a): return []
        def trigger_now(self, *a): pass

    import scheduler as sched_module   # noqa: PLC0415
    monkeypatch.setattr(sched_module, "get_scheduler", lambda *a, **kw: _FakeSched())

    import ws_publisher as pub_module  # noqa: PLC0415
    class _FakePub:
        def start(self): pass
        def stop(self):  pass

    monkeypatch.setattr(pub_module, "get_publisher", lambda *a, **kw: _FakePub())

    from main import app               # noqa: PLC0415
    with TestClient(app) as c:
        yield c

