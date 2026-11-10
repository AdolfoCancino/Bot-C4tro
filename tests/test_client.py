from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import discord
import pytest
from discord import app_commands

from bot import cogs
from bot.client import StatisticsBot
from bot.config import Settings


async def test_extensions_load_and_commands_require_permission(tmp_path):
    settings = Settings("offline-test-token", tmp_path / "db.sqlite3", guild_id=123)
    async with StatisticsBot(settings) as bot:
        with patch.object(bot.tree, "sync", new=AsyncMock(return_value=[])) as sync:
            await bot.setup_hook()
        sync.assert_awaited_once()
        assert sync.call_args.kwargs["guild"].id == 123
        assert set(bot.extensions) == {"bot.cogs.goals", "bot.cogs.tracking"}
        group = bot.tree.get_command("metas")
        assert group.default_permissions.manage_guild
        assert {command.name for command in group.commands} == {
            "publicar",
            "ver",
            "rol",
            "valor",
            "objetivo",
            "actualizar",
        }
        command = group.get_command("objetivo")
        interaction = SimpleNamespace(guild=object(), permissions=discord.Permissions.none())
        with pytest.raises(app_commands.MissingPermissions):
            await command._check_can_run(interaction)
        interaction.permissions = discord.Permissions(manage_guild=True)
        assert await command._check_can_run(interaction)
        interaction.guild = None
        with pytest.raises(app_commands.NoPrivateMessage):
            await command._check_can_run(interaction)


def test_token_is_required(monkeypatch):
    monkeypatch.setattr("bot.config.load_dotenv", lambda: None)
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    with pytest.raises(ValueError, match="Falta DISCORD_TOKEN"):
        Settings.from_env()


@pytest.mark.parametrize("guild_id", ["abc", "-1", "0"])
def test_invalid_guild_id_is_rejected(monkeypatch, guild_id):
    monkeypatch.setattr("bot.config.load_dotenv", lambda: None)
    monkeypatch.setenv("DISCORD_TOKEN", "offline-test-token")
    monkeypatch.setenv("DISCORD_GUILD_ID", guild_id)
    with pytest.raises(ValueError, match="DISCORD_GUILD_ID"):
        Settings.from_env()


def test_proxy_is_inherited_without_exposing_token(monkeypatch):
    monkeypatch.setattr("bot.config.load_dotenv", lambda: None)
    monkeypatch.setenv("DISCORD_TOKEN", "private-offline-test-token")
    monkeypatch.delenv("DISCORD_GUILD_ID", raising=False)
    monkeypatch.delenv("https_proxy", raising=False)
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example:8080")
    settings = Settings.from_env()
    assert settings.proxy_url == "http://proxy.example:8080"
    assert settings.token not in repr(settings)
    assert settings.proxy_url not in repr(settings)


async def test_new_feature_loads_from_an_independent_file(tmp_path, monkeypatch):
    extensions = tmp_path / "extensions"
    extensions.mkdir()
    (extensions / "example_feature.py").write_text(
        "from discord.ext import commands\n"
        "class ExampleFeature(commands.Cog):\n"
        "    pass\n"
        "async def setup(bot):\n"
        "    await bot.add_cog(ExampleFeature())\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cogs, "__path__", [*cogs.__path__, str(extensions)])
    async with StatisticsBot(Settings("offline-test-token", tmp_path / "db.sqlite3")) as bot:
        with patch.object(bot.tree, "sync", new=AsyncMock(return_value=[])) as sync:
            await bot.setup_hook()
        sync.assert_awaited_once_with()
        assert bot.get_cog("ExampleFeature") is not None
        assert "bot.cogs.example_feature" in bot.extensions
