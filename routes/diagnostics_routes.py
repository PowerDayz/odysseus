"""Diagnostics routes — app health, /api/db/stats, /api/rag/stats, and test helpers."""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Form

from services.youtube.youtube_handler import extract_youtube_id, extract_transcript_async
from core.constants import DEFAULT_HOST

logger = logging.getLogger(__name__)


def setup_diagnostics_routes(
    rag_manager,
    rag_available: bool,
    research_handler,
    memory_vector=None,
) -> APIRouter:
    router = APIRouter(tags=["diagnostics"])

    def _service(name: str, status: str, detail: str, **extra) -> Dict[str, Any]:
        item: Dict[str, Any] = {"name": name, "status": status, "detail": detail}
        item.update(extra)
        return item

    @router.get("/api/system/status")
    async def get_system_status() -> Dict[str, Any]:
        """Return a non-secret service readiness summary for the Settings → System panel."""
        services = []

        try:
            from core.database import SessionLocal, ModelEndpoint, EmailAccount

            db = SessionLocal()
            try:
                enabled_endpoints = db.query(ModelEndpoint).filter(ModelEndpoint.is_enabled == True).count()
                email_accounts = db.query(EmailAccount).count()
                enabled_email = db.query(EmailAccount).filter(EmailAccount.enabled == True).count()
            finally:
                db.close()

            services.append(_service("Database", "ok", "Application database is reachable."))
            services.append(_service(
                "Model providers",
                "ok" if enabled_endpoints else "warning",
                f"{enabled_endpoints} enabled endpoint(s) configured."
                if enabled_endpoints else
                "No enabled model endpoints configured. Add one in Settings → Services.",
                count=enabled_endpoints,
            ))
            services.append(_service(
                "Email",
                "ok" if enabled_email else ("warning" if email_accounts else "not_configured"),
                f"{enabled_email} enabled account(s), {email_accounts} total."
                if email_accounts else
                "No email accounts configured.",
                enabled=enabled_email,
                count=email_accounts,
            ))
        except Exception as exc:
            logger.warning("System status database checks failed: %s", exc)
            services.append(_service("Database", "error", "Application database check failed."))
            services.append(_service("Model providers", "unknown", "Endpoint configuration could not be read."))
            services.append(_service("Email", "unknown", "Email configuration could not be read."))

        if memory_vector and getattr(memory_vector, "healthy", False):
            try:
                count = memory_vector.count()
            except Exception:
                count = None
            detail = "ChromaDB vector memory is available."
            if count is not None:
                detail += f" {count} vector(s) indexed."
            services.append(_service("Semantic memory", "ok", detail, count=count))
        else:
            services.append(_service(
                "Semantic memory",
                "degraded",
                "ChromaDB vector memory is unavailable; keyword memory still works.",
            ))

        services.append(_service(
            "Document RAG",
            "ok" if rag_available and rag_manager else "disabled",
            "Vector document RAG is available."
            if rag_available and rag_manager else
            "Vector document RAG is disabled; document features use non-vector fallbacks.",
        ))

        try:
            from src.settings import load_settings
            from src.search.providers import PROVIDER_INFO

            settings = load_settings()
            provider = (settings.get("search_provider") or "disabled").strip()
            label, needs_key, needs_url = PROVIDER_INFO.get(provider, (provider or "Unknown", False, False))
            has_key = bool((settings.get({
                "brave": "brave_api_key",
                "google_pse": "google_pse_key",
                "tavily": "tavily_api_key",
                "serper": "serper_api_key",
            }.get(provider, "")) or "").strip())
            has_url = bool((settings.get("search_url") or "").strip())
            missing = (needs_key and not has_key) or (needs_url and not has_url and provider != "searxng")
            if provider == "disabled":
                status = "disabled"
                detail = "Web search is disabled."
            elif missing:
                status = "warning"
                detail = f"{label} is selected but required setup is incomplete."
            else:
                status = "ok"
                detail = f"{label} is selected for web search."
            services.append(_service("Web search", status, detail, provider=provider))
        except Exception as exc:
            logger.warning("System status search check failed: %s", exc)
            services.append(_service("Web search", "unknown", "Search settings could not be read."))

        try:
            from src.settings import load_settings

            settings = load_settings()
            channel = (settings.get("reminder_channel") or "browser").strip()
            topic = (settings.get("reminder_ntfy_topic") or "").strip()
            if channel == "ntfy" and not topic:
                services.append(_service("Notifications", "warning", "ntfy reminders are selected but no topic is configured."))
            else:
                services.append(_service("Notifications", "ok", f"{channel or 'browser'} reminder channel selected."))
        except Exception:
            services.append(_service("Notifications", "unknown", "Notification settings could not be read."))

        order = {"error": 0, "degraded": 1, "warning": 2, "unknown": 3, "disabled": 4, "not_configured": 5, "ok": 6}
        worst = min((s["status"] for s in services), key=lambda s: order.get(s, 9), default="ok")
        degraded = sum(1 for s in services if s["status"] in {"error", "degraded", "warning", "unknown"})
        return {"status": worst, "degraded_count": degraded, "services": services}

    @router.get("/api/db/stats")
    async def get_database_stats() -> Dict[str, Any]:
        try:
            from core.database import get_detailed_stats
            return get_detailed_stats()
        except Exception as e:
            logger.error(f"DB stats error: {e}")
            raise HTTPException(500, "Failed to retrieve database statistics")

    @router.get("/api/rag/stats")
    async def get_rag_stats() -> Dict[str, Any]:
        if rag_available and rag_manager:
            return rag_manager.get_stats()
        return {"error": "RAG system not available"}

    @router.get("/api/test/youtube")
    async def test_youtube(url: str) -> Dict[str, Any]:
        try:
            video_id = extract_youtube_id(url)
            if not video_id:
                return {"error": "Invalid YouTube URL"}

            data = await extract_transcript_async(url, video_id)
            return {
                "video_id": video_id,
                "transcript_success": data.get("success", False),
                "transcript_length": len(data.get("transcript", "")) if data.get("success") else 0,
                "transcript_preview": (data.get("transcript", "")[:500] + "...")
                    if data.get("success") and len(data.get("transcript", "")) > 500
                    else data.get("transcript", ""),
                "error": data.get("error") if not data.get("success") else None,
            }
        except Exception as e:
            return {"error": str(e)}

    @router.post("/api/test-research")
    async def test_research(query: str = Form("What is machine learning?")) -> Dict[str, Any]:
        try:
            endpoint = f"http://{DEFAULT_HOST}:8000/v1/chat/completions"
            model = "gpt-oss-120b"
            result = await research_handler.call_research_service(query, endpoint, model)
            return {
                "status": "success",
                "query": query,
                "result_preview": result[:200] + "..." if len(result) > 200 else result,
                "result_length": len(result),
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "query": query}

    return router
