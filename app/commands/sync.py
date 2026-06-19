from hydrogram import Client

from app.storage.diff import diff_states
from app.storage.io import read_filters, read_lock, write_filters, write_lock
from app.telegram.api import apply_state, fetch_state, search_channels


async def cmd_pull(client: Client) -> None:
    telegram_state = await fetch_state(client)

    try:
        local_state = read_filters()
        diff = diff_states(local_state, telegram_state)
        if not diff.is_empty:
            answer = input("Перезаписать? [y/N] ").strip().lower()
            if answer != "y":
                return
    except FileNotFoundError:
        pass

    write_filters(telegram_state)
    write_lock(telegram_state)


async def cmd_push(client: Client) -> None:
    try:
        local_state = read_filters()
    except FileNotFoundError:
        return

    lock_state = read_lock()
    telegram_state = await fetch_state(client)

    if lock_state is not None:
        external_diff = diff_states(lock_state, telegram_state)
        if not external_diff.is_empty:
            answer = input("Продолжить всё равно? [y/N] ").strip().lower()
            if answer != "y":
                return

    pending_diff = diff_states(telegram_state, local_state)
    if pending_diff.is_empty:
        return

    answer = input("Применить? [y/N] ").strip().lower()
    if answer != "y":
        return

    await apply_state(client, local_state)
    write_lock(local_state)


async def cmd_find_channel(client: Client, query: str) -> None:
    matches = await search_channels(client, query)
    if not matches:
        return
    for _m in matches:
        pass
