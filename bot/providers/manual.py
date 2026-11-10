import discord

from bot.providers import register
from bot.storage import Goal


@register("manual")
def manual(guild: discord.Guild, goal: Goal) -> int:
    return goal.value
