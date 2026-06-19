import tomllib
from pathlib import Path

import tomli_w

from app.mapper import state_from_dict, state_to_dict
from app.models import FiltersState

FILTERS_FILE = Path("filters.toml")
LOCK_FILE = Path("filters.lock.toml")


def read_filters(path: Path = FILTERS_FILE) -> FiltersState:
    """Читает filters.toml → FiltersState. Raises FileNotFoundError если нет файла."""
    if not path.exists():
        msg = f"{path} not found"
        raise FileNotFoundError(msg)
    with path.open("rb") as f:
        data = tomllib.load(f)
    return state_from_dict(data)


def write_filters(state: FiltersState, path: Path = FILTERS_FILE) -> None:
    """Записывает FiltersState → filters.toml."""
    path.write_bytes(tomli_w.dumps(state_to_dict(state)).encode())


def read_lock(path: Path = LOCK_FILE) -> FiltersState | None:
    """Читает filters.lock.toml. Возвращает None если файл не существует."""
    if not path.exists():
        return None
    with path.open("rb") as f:
        data = tomllib.load(f)
    return state_from_dict(data)


def write_lock(state: FiltersState, path: Path = LOCK_FILE) -> None:
    """Записывает filters.lock.toml."""
    path.write_bytes(tomli_w.dumps(state_to_dict(state)).encode())
