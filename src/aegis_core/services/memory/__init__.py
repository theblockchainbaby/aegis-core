"""memory service — Plan A stub. Real implementation in Plan C."""
from .._stub import StubService


def make_service(**kwargs) -> StubService:
    return StubService(name="memory", **kwargs)
