from types import SimpleNamespace

import pytest

from bot.presentation import render_board
from bot.providers import DataUnavailable, count
from bot.storage import Goal


def test_members_and_boosts_are_separate_counts(guild):
    guild.premium_subscription_count = 6
    assert count(guild, Goal("members", 1000, "members", None, 0)) == 116
    assert count(guild, Goal("boosts", 6, "boosts", None, 0)) == 6


def test_role_count_tracks_assignment_and_removal(guild):
    role = SimpleNamespace(members=[1, 2])
    guild.get_role = lambda _: role
    goal = Goal("raptor", 10, "role", 456, 0)
    assert count(guild, goal) == 2
    role.members.append(3)
    assert count(guild, goal) == 3
    role.members.remove(1)
    assert count(guild, goal) == 2


@pytest.mark.parametrize("role_id, chunked", [(None, True), (999, True), (456, False)])
def test_missing_or_incomplete_role_data_is_not_zero(guild, role_id, chunked):
    guild.chunked = chunked
    with pytest.raises(DataUnavailable):
        count(guild, Goal("raptor", 10, "role", role_id, 0))


def test_unknown_source_is_reported(guild):
    with pytest.raises(DataUnavailable):
        count(guild, Goal("raptor", 10, "missing_plugin", None, 0))


def test_render_achieved_goal_and_unconfigured_source(guild):
    embed = render_board(
        guild,
        [
            Goal("members", 100, "members", None, 0),
            Goal("raptor", 10, "role", None, 0),
            Goal("carno", 5, "manual", None, 2),
        ],
    )
    assert "116 / 100" in embed.fields[0].value
    assert "✅" in embed.fields[0].value
    assert "100%" in embed.fields[0].value
    assert "Sin configurar" in embed.fields[1].value
    assert "manual" in embed.fields[2].value
    assert "2 / 5" in embed.fields[2].value
