import discord

from bot.metrics import METRICS_BY_KEY
from bot.providers import DataUnavailable, count
from bot.storage import Goal


def render_board(guild: discord.Guild, goals: list[Goal]) -> discord.Embed:
    embed = discord.Embed(
        title="📊 Metas del servidor",
        description="¡Estas son las metas que queremos alcanzar juntos!",
        color=discord.Color.blurple(),
    )
    for goal in goals:
        label = METRICS_BY_KEY[goal.key].label
        try:
            value = count(guild, goal)
        except DataUnavailable as exc:
            text = f"**— / {goal.target}**\n{exc}"
        else:
            progress = min(value / goal.target, 1)
            filled = int(progress * 10)
            bar = "▰" * filled + "▱" * (10 - filled)
            status = "✅ " if value >= goal.target else ""
            source = " · manual" if goal.source == "manual" else ""
            text = f"{status}**{value} / {goal.target}**{source}\n{bar} {progress:.0%}"
        embed.add_field(name=label, value=text, inline=False)
    embed.set_footer(text="Actualización automática · Los miembros incluyen bots")
    return embed
