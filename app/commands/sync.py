from hydrogram import Client

from app.storage.diff import diff_states, format_diff
from app.storage.io import read_filters, read_lock, write_filters, write_lock
from app.telegram.api import apply_state, fetch_state, search_channels


async def cmd_pull(client: Client) -> None:
    telegram_state = await fetch_state(client)

    try:
        local_state = read_filters()
        diff = diff_states(local_state, telegram_state)
        if not diff.is_empty:
            print("Локальный filters.toml отличается от Telegram:")
            print(format_diff(diff))
            answer = input("Перезаписать? [y/N] ").strip().lower()
            if answer != "y":
                print("Отменено.")
                return
    except FileNotFoundError:
        pass

    write_filters(telegram_state)
    write_lock(telegram_state)
    print("filters.toml и filters.lock.toml обновлены.")


async def cmd_push(client: Client) -> None:
    try:
        local_state = read_filters()
    except FileNotFoundError:
        print("Ошибка: filters.toml не найден. Сначала выполните pull.")
        return

    lock_state = read_lock()
    telegram_state = await fetch_state(client)

    if lock_state is not None:
        external_diff = diff_states(lock_state, telegram_state)
        if not external_diff.is_empty:
            print("Telegram был изменён извне после последнего pull:")
            print(format_diff(external_diff))
            answer = input("Продолжить всё равно? [y/N] ").strip().lower()
            if answer != "y":
                print("Отменено.")
                return

    pending_diff = diff_states(telegram_state, local_state)
    if pending_diff.is_empty:
        print("Изменений нет.")
        return

    print("Будет применено:")
    print(format_diff(pending_diff))
    answer = input("Применить? [y/N] ").strip().lower()
    if answer != "y":
        print("Отменено.")
        return

    await apply_state(client, local_state)
    write_lock(local_state)
    print("Готово.")


async def cmd_find_channel(client: Client, query: str) -> None:
    matches = await search_channels(client, query)
    if not matches:
        print("Ничего не найдено.")
        return
    for m in matches:
        username_str = f"@{m.username}" if m.username else "(private)"
        print(f'{m.chat_id:<15} {username_str:<30} "{m.title}"')
