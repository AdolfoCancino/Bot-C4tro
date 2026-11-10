import logging

import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)


class Tracking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ticks = 0

    async def cog_load(self):
        self.update_boards.start()

    async def cog_unload(self):
        self.update_boards.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            self.bot.boards.mark_dirty(guild.id)

    @commands.Cog.listener()
    async def on_guild_available(self, guild: discord.Guild):
        self.bot.boards.mark_dirty(guild.id)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        self.bot.boards.mark_dirty(member.guild.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        self.bot.boards.mark_dirty(member.guild.id)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.roles != after.roles or before.premium_since != after.premium_since:
            self.bot.boards.mark_dirty(after.guild.id)

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        if before.premium_subscription_count != after.premium_subscription_count:
            self.bot.boards.mark_dirty(after.id)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        self.bot.boards.mark_dirty(role.guild.id)

    @tasks.loop(seconds=10)
    async def update_boards(self):
        try:
            # Reconciliación periódica para recuperar eventos perdidos tras reconexiones.
            if self.ticks % 30 == 0:
                for board in await self.bot.store.boards():
                    self.bot.boards.mark_dirty(board.guild_id)
            self.ticks += 1
            await self.bot.boards.flush()
        except Exception:
            log.exception("Falló el ciclo de actualización; se reintentará en el siguiente ciclo")

    @update_boards.before_loop
    async def before_update(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Tracking(bot))
