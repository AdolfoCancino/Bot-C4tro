import asyncio

import pytest

from bot.storage import Board, Store


async def test_defaults_and_guild_isolation(store):
    goals = {g.key: g for g in await store.goals(1)}
    assert {k: g.target for k, g in goals.items()} == {
        "members": 1000,
        "boosts": 6,
        "raptor": 10,
        "cera": 7,
        "carno": 5,
        "spino": 3,
        "trex": 2,
        "deino": 1,
    }
    await store.configure(1, "raptor", role_id=42, target=20)
    first = {g.key: g for g in await store.goals(1)}
    other = {g.key: g for g in await store.goals(2)}
    assert (first["raptor"].role_id, first["raptor"].target) == (42, 20)
    assert (other["raptor"].role_id, other["raptor"].target) == (None, 10)


async def test_config_and_board_survive_restart(tmp_path):
    path = tmp_path / "persistent.sqlite3"
    first = await Store.open(path)
    await first.configure(1, "raptor", value=4, target=12)
    await first.save_board(Board(1, 22, 33))
    await first.close()
    second = await Store.open(path)
    try:
        raptor = next(g for g in await second.goals(1) if g.key == "raptor")
        assert (raptor.source, raptor.value, raptor.target) == ("manual", 4, 12)
        assert await second.board(1) == Board(1, 22, 33)
        assert await second.boards() == [Board(1, 22, 33)]
        await second.remove_board(1)
        assert await second.board(1) is None
    finally:
        await second.close()


async def test_manual_and_role_switch_preserve_target(store):
    await store.configure(1, "carno", target=9, role_id=42)
    await store.configure(1, "carno", value=0)
    goal = next(g for g in await store.goals(1) if g.key == "carno")
    assert (goal.source, goal.role_id, goal.value, goal.target) == ("manual", None, 0, 9)
    await store.configure(1, "carno", role_id=51)
    goal = next(g for g in await store.goals(1) if g.key == "carno")
    assert (goal.source, goal.role_id, goal.target) == ("role", 51, 9)


@pytest.mark.parametrize(
    "key, kwargs",
    [
        ("raptor", {"target": 0}),
        ("raptor", {"value": -1}),
        ("raptor", {"role_id": 0}),
        ("raptor", {"value": 1, "role_id": 10}),
        ("members", {"value": 5}),
        ("boosts", {"role_id": 123}),
    ],
)
async def test_reject_invalid_configuration(store, key, kwargs):
    with pytest.raises(ValueError):
        await store.configure(1, key, **kwargs)


async def test_concurrent_guild_configuration(store):
    await asyncio.gather(*(store.configure(i, "raptor", value=i) for i in range(10)))
    for i in range(10):
        goal = next(g for g in await store.goals(i) if g.key == "raptor")
        assert goal.value == i
