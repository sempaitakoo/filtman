from pathlib import Path

import tomlkit
import tomlkit.items

from app.mapper import LIST_FIELDS, state_from_dict, state_to_dict
from app.models import FiltersState, PeerUniverse

FILTERS_FILE = Path("filters.toml")
LOCK_FILE = Path("filters.lock.toml")


def read_filters(path: Path = FILTERS_FILE) -> FiltersState:
    """Читает filters.toml → FiltersState. Raises FileNotFoundError если нет файла."""
    if not path.exists():
        msg = f"{path} not found"
        raise FileNotFoundError(msg)
    return state_from_dict(tomlkit.parse(path.read_text()))


def write_filters(
    state: FiltersState,
    path: Path = FILTERS_FILE,
    universe: PeerUniverse | None = None,
) -> None:
    """Записывает FiltersState → filters.toml. Если передан universe — добавляет комментарии с именами чатов."""
    names = universe.by_id() if universe else {}
    data = state_to_dict(state)

    doc = tomlkit.document()
    filters_table = tomlkit.table(is_super_table=True)

    for fid_str, entry in data["filters"].items():
        t = tomlkit.table()
        t.add("title", entry["title"])
        for list_field in LIST_FIELDS:
            if list_field not in entry:
                continue
            ids: list[int] = entry[list_field]
            if names:
                arr = tomlkit.array()
                arr.multiline(True)  # noqa: FBT003
                for chat_id in ids:
                    arr.append(chat_id)
                    peer = names.get(chat_id)
                    if peer:
                        trivia = tomlkit.items.Trivia(
                            indent=" ", comment=f"# {peer.name}", trail=""
                        )
                        arr._value[-1].comment = tomlkit.items.Comment(trivia)  # type: ignore[index]  # noqa: SLF001
                t.add(list_field, arr)
            else:
                t.add(list_field, ids)
        for key, val in entry.items():
            if key in ("title", *LIST_FIELDS):
                continue
            t.add(key, val)
        filters_table.add(fid_str, t)

    doc.add("filters", filters_table)
    path.write_text(tomlkit.dumps(doc))


def read_lock(path: Path = LOCK_FILE) -> FiltersState | None:
    """Читает filters.lock.toml. Возвращает None если файл не существует."""
    if not path.exists():
        return None
    return state_from_dict(tomlkit.parse(path.read_text()))


def write_lock(state: FiltersState, path: Path = LOCK_FILE) -> None:
    """Записывает filters.lock.toml."""
    data = state_to_dict(state)
    path.write_text(tomlkit.dumps({"filters": data["filters"]}))
