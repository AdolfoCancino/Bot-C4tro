"""Cada archivo registra fuentes de datos sin modificar los comandos ni el panel."""

import importlib
import pkgutil
from collections.abc import Callable

import discord

from bot.storage import Goal

Provider = Callable[[discord.Guild, Goal], int]
REGISTRY: dict[str, Provider] = {}


class DataUnavailable(Exception):
    """La fuente todavía no puede entregar un contador fiable."""


def register(name: str):
    def decorator(provider: Provider) -> Provider:
        if name in REGISTRY:
            raise ValueError(f"Fuente duplicada: {name}")
        REGISTRY[name] = provider
        return provider

    return decorator


def load_providers() -> None:
    for module in sorted(pkgutil.iter_modules(__path__), key=lambda item: item.name):
        if not module.name.startswith("_"):
            importlib.import_module(f"{__name__}.{module.name}")


def count(guild: discord.Guild, goal: Goal) -> int:
    provider = REGISTRY.get(goal.source)
    if provider is None:
        raise DataUnavailable("Fuente no disponible")
    return provider(guild, goal)
