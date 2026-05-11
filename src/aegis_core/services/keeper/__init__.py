"""keeper service — Plan A stub. Real implementation in Plan F."""
from .._stub import StubService


def make_service(**kwargs) -> StubService:
    return StubService(name="keeper", **kwargs)
