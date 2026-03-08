"""Router sub-package – re-export modules for convenient imports."""

from app.routers import alerts, auth, dashboard, events, reports

__all__ = ["alerts", "auth", "dashboard", "events", "reports"]
