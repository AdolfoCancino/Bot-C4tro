import discord

from bot.providers import DataUnavailable, register
from bot.storage import Goal


@register("members")
def members(guild: discord.Guild, goal: Goal) -> int:
    if guild.member_count is None:
        raise DataUnavailable("Esperando datos de Discord")
    return guild.member_count


@register("boosts")
def boosts(guild: discord.Guild, goal: Goal) -> int:
    return guild.premium_subscription_count or 0


@register("role")
def role_members(guild: discord.Guild, goal: Goal) -> int:
    if goal.role_id is None:
        raise DataUnavailable("Sin configurar: /metas rol o /metas valor")
    role = guild.get_role(goal.role_id)
    if role is None:
        raise DataUnavailable("Rol eliminado: configura otro con /metas rol")
    if not guild.chunked:
        raise DataUnavailable("Esperando la lista completa de miembros")
    return len(role.members)
