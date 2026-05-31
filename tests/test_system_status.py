import sys
import types

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes.diagnostics_routes import setup_diagnostics_routes


class _FakeQuery:
    def __init__(self, count):
        self._count = count

    def filter(self, *_args, **_kwargs):
        return self

    def count(self):
        return self._count


class _FakeDb:
    def __init__(self, endpoint_count=0, email_count=0):
        self.endpoint_count = endpoint_count
        self.email_count = email_count

    def query(self, model):
        if getattr(model, "__name__", "") == "ModelEndpoint":
            return _FakeQuery(self.endpoint_count)
        if getattr(model, "__name__", "") == "EmailAccount":
            return _FakeQuery(self.email_count)
        return _FakeQuery(0)

    def close(self):
        pass


class _ModelEndpoint:
    is_enabled = True


class _EmailAccount:
    enabled = True


def _install_fake_database(monkeypatch, endpoint_count=0, email_count=0):
    mod = types.ModuleType("core.database")
    mod.ModelEndpoint = _ModelEndpoint
    mod.EmailAccount = _EmailAccount
    mod.SessionLocal = lambda: _FakeDb(endpoint_count=endpoint_count, email_count=email_count)
    monkeypatch.setitem(sys.modules, "core.database", mod)


def test_system_status_reports_degraded_memory_and_setup_gaps(monkeypatch):
    _install_fake_database(monkeypatch, endpoint_count=0, email_count=0)
    monkeypatch.setattr(
        "src.settings.load_settings",
        lambda: {"search_provider": "searxng", "reminder_channel": "browser"},
    )

    app = FastAPI()
    app.include_router(setup_diagnostics_routes(None, False, object(), memory_vector=None))

    data = TestClient(app).get("/api/system/status").json()

    assert data["degraded_count"] >= 2
    services = {item["name"]: item for item in data["services"]}
    assert services["Semantic memory"]["status"] == "degraded"
    assert services["Model providers"]["status"] == "warning"
    assert services["Email"]["status"] == "not_configured"


def test_system_status_reports_available_configured_services(monkeypatch):
    _install_fake_database(monkeypatch, endpoint_count=2, email_count=1)
    monkeypatch.setattr(
        "src.settings.load_settings",
        lambda: {"search_provider": "duckduckgo", "reminder_channel": "browser"},
    )

    class HealthyMemory:
        healthy = True

        def count(self):
            return 3

    app = FastAPI()
    app.include_router(setup_diagnostics_routes(object(), True, object(), memory_vector=HealthyMemory()))

    data = TestClient(app).get("/api/system/status").json()
    services = {item["name"]: item for item in data["services"]}

    assert services["Semantic memory"]["status"] == "ok"
    assert services["Semantic memory"]["count"] == 3
    assert services["Model providers"]["status"] == "ok"
    assert services["Email"]["status"] == "ok"
    assert services["Document RAG"]["status"] == "ok"
