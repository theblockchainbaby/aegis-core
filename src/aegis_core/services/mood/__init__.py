"""mood service — Plan A stub. Real implementation in Plan E."""
from .._stub import StubService


def make_service(**kwargs) -> StubService:
    return StubService(name="mood", **kwargs)
