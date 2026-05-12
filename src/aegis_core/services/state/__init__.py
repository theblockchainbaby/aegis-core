"""state service — Presence State Machine on the NATS bus."""
from .service import StateService, make_service

__all__ = ["StateService", "make_service"]
