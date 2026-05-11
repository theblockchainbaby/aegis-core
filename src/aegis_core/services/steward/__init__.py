"""steward service — Plan A stub. Real implementation in Plan D."""
from .._stub import StubService


def make_service(**kwargs) -> StubService:
    return StubService(name="steward", **kwargs)
