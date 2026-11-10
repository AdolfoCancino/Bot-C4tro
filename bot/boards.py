import asyncio
import logging
from collections import defaultdict

import discord

from bot.presentation import render_board
from bot.storage import Board, Store

log = logging.getLogger(__name__)


class BoardService:
    def __init__(self, client: discord.Client, store: Store):
        self.client = client
        self.store = store
        self.dirty: set[int] = set()
        self.locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    def mark_dirty(self, guild_id: int) -> None:
        self.dirty.add(guild_id)

    async def embed(self, guild: discord.Guild) -> discord.Embed:
        return render_board(guild, await self.store.goals(guild.id))

    async def _message(self, board: Board) -> discord.Message:
        channel = self.client.get_channel(board.channel_id)
        if channel is None:
            channel = await self.client.fetch_channel(board.channel_id)
        if not isinstance(channel, discord.TextChannel) or channel.guild.id != board.guild_id:
            raise ValueError("El canal del panel debe ser un canal de texto del servidor.")
        return await channel.fetch_message(board.message_id)

    async def publish(self, guild: discord.Guild, channel: discord.TextChannel) -> str:
        async with self.locks[guild.id]:
            existing = await self.store.board(guild.id)
            if existing:
                try:
                    message = await self._message(existing)
                except discord.NotFound:
                    await self.store.remove_board(guild.id)
                else:
                    await message.edit(embed=await self.embed(guild))
                    return message.jump_url
            message = await channel.send(
                embed=await self.embed(guild),
                allowed_mentions=discord.AllowedMentions.none(),
            )
            await self.store.save_board(Board(guild.id, channel.id, message.id))
            return message.jump_url

    async def refresh(self, guild_id: int) -> None:
        async with self.locks[guild_id]:
            board = await self.store.board(guild_id)
            guild = self.client.get_guild(guild_id)
            if board is None or guild is None:
                return
            try:
                message = await self._message(board)
                embed = await self.embed(guild)
                if not message.embeds or message.embeds[0].to_dict() != embed.to_dict():
                    await message.edit(embed=embed)
            except discord.NotFound:
                await self.store.remove_board(guild_id)
                log.warning(
                    "Panel eliminado en servidor %s; vuelve a usar /metas publicar", guild_id
                )

    async def flush(self) -> None:
        # Retirar antes del await conserva los eventos recibidos durante una actualización.
        pending = self.dirty.copy()
        self.dirty.difference_update(pending)
        for guild_id in pending:
            try:
                await self.refresh(guild_id)
            except (discord.HTTPException, ValueError):
                self.mark_dirty(guild_id)
                log.warning(
                    "No se pudo actualizar el panel del servidor %s", guild_id, exc_info=True
                )
