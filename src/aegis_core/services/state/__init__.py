"""state service — Plan A stub. Real implementation in Plan B."""
from .._stub import StubService


def make_service(**kwargs) -> StubService:
    return StubService(name="state", **kwargs)
