from typing import Annotated

import cyclopts
from hydrogram import Client

from app.commands.local import cmd_annotate, cmd_compact, cmd_diff, cmd_exclude
from app.commands.sync import cmd_find_channel, cmd_pull, cmd_push
from app.config import settings

app = cyclopts.App()


def get_client() -> Client:
    return Client(
        settings.session_path,
        api_id=settings.API_ID,
        api_hash=settings.API_HASH,
    )


@app.command
def annotate() -> None:
    """Добавить комментарии с именами чатов в filters.toml из peers.lock.json."""
    cmd_annotate()


@app.command
def diff() -> None:
    """Показать diff между filters.toml и filters.lock.toml."""
    cmd_diff()


@app.command
def compact(filter_id: int | None = None) -> None:
    """Показать (и применить) упрощения filters.toml через флаги категорий."""
    cmd_compact(filter_id)


@app.command
def exclude(
    target_id: int,
    from_: Annotated[int, cyclopts.Parameter(name="--from")],
) -> None:
    """Добавить в exclude фильтра <target_id> все peers из фильтра --from."""
    cmd_exclude(target_id, from_)


@app.command
async def pull() -> None:
    """Скачать фильтры из Telegram в filters.toml."""
    async with get_client() as client:
        await cmd_pull(client)


@app.command
async def push() -> None:
    """Применить filters.toml к Telegram."""
    async with get_client() as client:
        await cmd_push(client)


@app.command(name="find-channel")
async def find_channel(query: str) -> None:
    """Найти канал среди диалогов по названию."""
    async with get_client() as client:
        await cmd_find_channel(client, query)
