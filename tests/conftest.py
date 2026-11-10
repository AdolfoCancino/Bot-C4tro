from types import SimpleNamespace
from unittest.mock import MagicMock

import discord
import pytest
import pytest_asyncio

from bot.providers import load_providers
from bot.storage import Store


@pytest.fixture(autouse=True)
def providers():
    load_providers()


@pytest_asyncio.fixture
async def store(tmp_path):
    instance = await Store.open(tmp_path / "test.sqlite3")
    yield instance
    await instance.close()


@pytest.fixture
def guild():
    role = SimpleNamespace(members=[object(), object(), object()])
    return SimpleNamespace(
        id=123,
        member_count=116,
        premium_subscription_count=0,
        chunked=True,
        get_role=lambda role_id: role if role_id == 456 else None,
    )


@pytest.fixture
def channel(guild):
    result = MagicMock(spec=discord.TextChannel)
    result.id = 789
    result.guild = guild
    return result
