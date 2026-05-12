from pathlib import Path

from aegis_core.storage._conn import connect
from aegis_core.storage.scar_tissue import ScarTissueStore
from aegis_core.storage.schema import run_migrations


def test_unknown_class_returns_zero_penalty(tmp_path: Path):
    conn = connect(tmp_path / "m.db")
    run_migrations(conn)
    store = ScarTissueStore(conn)
    assert store.get_penalty("ambient_note") == 0.0
    conn.close()


def test_bump_veto_accumulates(tmp_path: Path):
    conn = connect(tmp_path / "m.db")
    run_migrations(conn)
    store = ScarTissueStore(conn)
    store.bump_veto("memory_magic", by=0.03)
    store.bump_veto("memory_magic", by=0.03)
    assert abs(store.get_penalty("memory_magic") - 0.06) < 1e-6
    conn.close()


def test_bump_unacknowledged_accumulates(tmp_path: Path):
    conn = connect(tmp_path / "m.db")
    run_migrations(conn)
    store = ScarTissueStore(conn)
    store.bump_unacknowledged("memory_magic", by=0.05)
    store.bump_unacknowledged("memory_magic", by=0.05)
    assert abs(store.get_penalty("memory_magic") - 0.10) < 1e-6
    conn.close()


def test_recover_decreases_but_floors_at_zero(tmp_path: Path):
    conn = connect(tmp_path / "m.db")
    run_migrations(conn)
    store = ScarTissueStore(conn)
    store.bump_veto("memory_magic", by=0.03)
    store.recover("memory_magic", by=0.07)
    assert store.get_penalty("memory_magic") == 0.0  # floor
    conn.close()


def test_cap_applied_on_bump(tmp_path: Path):
    conn = connect(tmp_path / "m.db")
    run_migrations(conn)
    store = ScarTissueStore(conn)
    for _ in range(20):
        store.bump_veto("memory_magic", by=0.03, cap=0.15)
    assert abs(store.get_penalty("memory_magic") - 0.15) < 1e-6
    conn.close()


def test_all_classes_returns_dict(tmp_path: Path):
    conn = connect(tmp_path / "m.db")
    run_migrations(conn)
    store = ScarTissueStore(conn)
    store.bump_veto("a", by=0.03)
    store.bump_veto("b", by=0.06)
    out = store.all_classes()
    assert out == {"a": 0.03, "b": 0.06} or all(
        abs(out[k] - v) < 1e-6 for k, v in {"a": 0.03, "b": 0.06}.items()
    )
    conn.close()
