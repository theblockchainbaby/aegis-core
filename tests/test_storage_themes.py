from pathlib import Path

from aegis_core.storage._conn import connect
from aegis_core.storage.schema import run_migrations
from aegis_core.storage.themes import ThemeStore


def test_upsert_increments_count(tmp_path: Path):
    conn = connect(tmp_path / "t.db")
    run_migrations(conn)
    store = ThemeStore(conn)

    store.upsert("landing_page_redesign")
    store.upsert("landing_page_redesign")
    store.upsert("morning_focus")

    rows = store.query()
    by_key = {r["key"]: r["reinforcement_count"] for r in rows}
    assert by_key["landing_page_redesign"] == 2
    assert by_key["morning_focus"] == 1


def test_query_orders_by_count_desc(tmp_path: Path):
    conn = connect(tmp_path / "t.db")
    run_migrations(conn)
    store = ThemeStore(conn)
    store.upsert("a")
    for _ in range(5):
        store.upsert("b")
    for _ in range(3):
        store.upsert("c")

    rows = store.query()
    keys_in_order = [r["key"] for r in rows]
    assert keys_in_order == ["b", "c", "a"]


def test_decay_drops_unused(tmp_path: Path):
    conn = connect(tmp_path / "t.db")
    run_migrations(conn)
    store = ThemeStore(conn)
    store.upsert("a")
    store.upsert("b")
    store.upsert("b")
    store.decay(decrement=1)
    rows = {r["key"]: r["reinforcement_count"] for r in store.query()}
    # 'a' decayed to 0 → removed; 'b' still has 1
    assert "a" not in rows
    assert rows["b"] == 1
