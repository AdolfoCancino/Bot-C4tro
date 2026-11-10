from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord

from bot.boards import BoardService
from bot.cogs.tracking import Tracking
from bot.storage import Board


def fake_client(guild, channel):
    return SimpleNamespace(get_guild=lambda _: guild, get_channel=lambda _: channel)


def fake_message():
    return SimpleNamespace(
        id=999,
        jump_url="https://discord.com/channels/123/789/999",
        embeds=[],
        edit=AsyncMock(),
    )


async def test_publish_and_update_same_message(store, guild, channel):
    message = fake_message()
    channel.send.return_value = message
    channel.fetch_message.return_value = message
    service = BoardService(fake_client(guild, channel), store)
    assert await service.publish(guild, channel) == message.jump_url
    assert await store.board(guild.id) == Board(guild.id, channel.id, message.id)
    await store.configure(guild.id, "raptor", role_id=456)
    await service.publish(guild, channel)
    channel.send.assert_awaited_once()
    embed = message.edit.call_args.kwargs["embed"]
    assert "3 / 10" in embed.fields[2].value

    # Un reinicio conserva el ID y edita el mismo mensaje al llegar un evento.
    restarted = BoardService(fake_client(guild, channel), store)
    tracker = Tracking(SimpleNamespace(boards=restarted))
    guild.member_count = 117
    await tracker.on_member_join(SimpleNamespace(guild=guild))
    await restarted.flush()
    assert "117 / 1000" in message.edit.call_args.kwargs["embed"].fields[0].value
    channel.send.assert_awaited_once()


async def test_unchanged_board_is_not_edited(store, guild, channel):
    service = BoardService(fake_client(guild, channel), store)
    message = fake_message()
    message.embeds = [await service.embed(guild)]
    channel.fetch_message.return_value = message
    await store.save_board(Board(guild.id, channel.id, message.id))
    await service.refresh(guild.id)
    message.edit.assert_not_awaited()


async def test_deleted_message_can_be_republished(store, guild, channel):
    await store.save_board(Board(guild.id, channel.id, 111))
    response = SimpleNamespace(status=404, reason="Not Found")
    channel.fetch_message.side_effect = discord.NotFound(response, "Unknown Message")
    channel.send.return_value = fake_message()
    service = BoardService(fake_client(guild, channel), store)
    await service.refresh(guild.id)
    assert await store.board(guild.id) is None
    await service.publish(guild, channel)
    assert (await store.board(guild.id)).message_id == 999


async def test_transient_failure_retains_board_and_retries(store, guild, channel):
    await store.save_board(Board(guild.id, channel.id, 999))
    response = SimpleNamespace(status=403, reason="Forbidden")
    channel.fetch_message.side_effect = discord.Forbidden(response, "Missing Permissions")
    service = BoardService(fake_client(guild, channel), store)
    service.mark_dirty(guild.id)
    await service.flush()
    assert guild.id in service.dirty
    assert await store.board(guild.id) is not None
    channel.fetch_message.side_effect = None
    channel.fetch_message.return_value = fake_message()
    await service.flush()
    assert guild.id not in service.dirty


async def test_events_during_refresh_are_not_lost(store, guild, channel):
    service = BoardService(fake_client(guild, channel), store)

    async def refresh(guild_id):
        service.mark_dirty(guild_id)

    service.refresh = AsyncMock(side_effect=refresh)
    service.mark_dirty(guild.id)
    await service.flush()
    assert guild.id in service.dirty


async def test_role_and_boost_events_trigger_updates():
    boards = MagicMock()
    tracker = Tracking(SimpleNamespace(boards=boards))
    guild = SimpleNamespace(id=123)
    await tracker.on_member_update(
        SimpleNamespace(roles=[1], premium_since=None),
        SimpleNamespace(roles=[1, 2], premium_since=None, guild=guild),
    )
    boards.mark_dirty.assert_called_with(123)
    boards.reset_mock()
    await tracker.on_guild_update(
        SimpleNamespace(premium_subscription_count=0),
        SimpleNamespace(id=123, premium_subscription_count=2),
    )
    boards.mark_dirty.assert_called_once_with(123)
