import cyclopts
from hydrogram import Client

from app.commands.sync import cmd_find_channel, cmd_pull, cmd_push
from app.config import settings

app = cyclopts.App()


def get_client() -> Client:
    return Client(
        settings.SESSION_NAME,
        api_id=settings.API_ID,
        api_hash=settings.API_HASH,
    )


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


if __name__ == "__main__":
    app()
