import discord
from discord import app_commands
from discord.ext import commands

from bot.metrics import METRICS

ALL_CHOICES = [app_commands.Choice(name=m.label, value=m.key) for m in METRICS]
CUSTOM_CHOICES = [
    app_commands.Choice(name=m.label, value=m.key)
    for m in METRICS
    if m.source not in {"members", "boosts"}
]


@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
class Goals(commands.GroupCog, group_name="metas", group_description="Configurar las metas"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # También comprobar en ejecución aunque un admin cambie permisos de comandos.
        if interaction.guild is None:
            raise app_commands.NoPrivateMessage()
        if not interaction.permissions.manage_guild:
            raise app_commands.MissingPermissions(["manage_guild"])
        return True

    @app_commands.command(
        description="Publicar el panel automático en este canal (uno por servidor)"
    )
    async def publicar(self, interaction: discord.Interaction):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "Usa un canal de texto del servidor.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        url = await self.bot.boards.publish(interaction.guild, interaction.channel)
        await interaction.followup.send(f"Panel configurado: {url}", ephemeral=True)

    @app_commands.command(description="Ver las estadísticas actuales sin publicar un panel")
    async def ver(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send(
            embed=await self.bot.boards.embed(interaction.guild),
            ephemeral=True,
        )

    @app_commands.command(description="Contar automáticamente los miembros que tienen un rol")
    @app_commands.choices(estadistica=CUSTOM_CHOICES)
    async def rol(
        self,
        interaction: discord.Interaction,
        estadistica: str,
        rol: discord.Role,
    ):
        if rol.is_default():
            await interaction.response.send_message(
                "Elige un rol distinto de @everyone.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.bot.store.configure(interaction.guild_id, estadistica, role_id=rol.id)
        self.bot.boards.mark_dirty(interaction.guild_id)
        await interaction.followup.send(
            f"{estadistica}: se contarán los miembros con el rol {rol.mention}.",
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(description="Establecer un contador manual (sustituye el conteo por rol)")
    @app_commands.choices(estadistica=CUSTOM_CHOICES)
    async def valor(
        self,
        interaction: discord.Interaction,
        estadistica: str,
        cantidad: app_commands.Range[int, 0, 1_000_000_000],
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.bot.store.configure(interaction.guild_id, estadistica, value=cantidad)
        self.bot.boards.mark_dirty(interaction.guild_id)
        await interaction.followup.send(
            f"{estadistica}: contador manual en {cantidad}. Usa /metas rol para automatizarlo.",
            ephemeral=True,
        )

    @app_commands.command(description="Cambiar la meta de una estadística")
    @app_commands.choices(estadistica=ALL_CHOICES)
    async def objetivo(
        self,
        interaction: discord.Interaction,
        estadistica: str,
        cantidad: app_commands.Range[int, 1, 1_000_000_000],
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.bot.store.configure(interaction.guild_id, estadistica, target=cantidad)
        self.bot.boards.mark_dirty(interaction.guild_id)
        await interaction.followup.send(f"Meta de {estadistica}: {cantidad}.", ephemeral=True)

    @app_commands.command(description="Actualizar el panel ahora")
    async def actualizar(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if await self.bot.store.board(interaction.guild_id) is None:
            await interaction.followup.send("Primero usa /metas publicar.", ephemeral=True)
            return
        await self.bot.boards.refresh(interaction.guild_id)
        await interaction.followup.send(
            "Actualización terminada. Si el mensaje se eliminó, usa /metas publicar.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Goals(bot))
