from aegis_core import cli
from aegis_core.services.senses import make_service as senses_factory
from aegis_core.services.senses.service import SensesService
from aegis_core.services.state import make_service as state_factory
from aegis_core.services.state.service import StateService


def test_make_service_for_attaches_host_source_to_senses_on_darwin():
    service = cli._make_service_for(
        "senses", senses_factory, "nats://127.0.0.1:4222", platform="darwin"
    )
    assert isinstance(service, SensesService)
    assert len(service._sources) == 1
    assert service._sources[0].name == "host_activity"


def test_make_service_for_senses_has_no_source_off_darwin():
    service = cli._make_service_for(
        "senses", senses_factory, "nats://127.0.0.1:4222", platform="linux"
    )
    assert isinstance(service, SensesService)
    assert len(service._sources) == 0


def test_make_service_for_other_service_is_unchanged():
    service = cli._make_service_for(
        "state", state_factory, "nats://127.0.0.1:4222", platform="darwin"
    )
    assert isinstance(service, StateService)
