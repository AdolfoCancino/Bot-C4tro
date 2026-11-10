import logging
import pkgutil

import discord
from discord import app_commands
from discord.ext import commands

from bot import cogs
from bot.boards import BoardService
from bot.config import Settings
from bot.providers import load_providers
from bot.storage import Store

log = logging.getLogger(__name__)


class StatisticsBot(commands.Bot):
    def __init__(self, settings: Settings):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            allowed_mentions=discord.AllowedMentions.none(),
            proxy=settings.proxy_url,
        )
        self.settings = settings
        self.store: Store | None = None
        self.boards: BoardService | None = None
        self.tree.on_error = self.on_app_command_error

    async def setup_hook(self):
        self.store = await Store.open(self.settings.database_path)
        self.boards = BoardService(self, self.store)
        load_providers()
        for module in sorted(pkgutil.iter_modules(cogs.__path__), key=lambda item: item.name):
            if not module.name.startswith("_"):
                await self.load_extension(f"bot.cogs.{module.name}")
        if self.settings.guild_id:
            guild = discord.Object(id=self.settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
        else:
            synced = await self.tree.sync()
        log.info("Sincronizados %s grupos/comandos", len(synced))

    async def on_ready(self):
        log.info("Bot conectado: %s · %s servidores", self.user, len(self.guilds))

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ):
        cause = getattr(error, "original", error)
        if isinstance(cause, app_commands.MissingPermissions):
            text = "Necesitas el permiso Gestionar servidor para configurar las metas."
        elif isinstance(cause, app_commands.NoPrivateMessage):
            text = "Usa este comando dentro de un servidor."
        elif isinstance(cause, discord.Forbidden):
            text = (
                "No tengo permisos suficientes. Revisa Ver canal, Enviar mensajes, "
                "Insertar enlaces y Leer el historial de mensajes en el canal del panel."
            )
        elif isinstance(cause, (ValueError, KeyError)):
            text = "Configuración no válida. Revisa la estadística y los valores seleccionados."
        else:
            log.error("Falló un comando", exc_info=(type(error), error, error.__traceback__))
            text = (
                "No se pudo completar el comando. "
                "Revisa los registros del bot e inténtalo otra vez."
            )
        if interaction.response.is_done():
            await interaction.followup.send(text, ephemeral=True)
        else:
            await interaction.response.send_message(text, ephemeral=True)

    async def close(self):
        try:
            await super().close()
        finally:
            if self.store is not None:
                await self.store.close()
                self.store = None
