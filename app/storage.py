import tomllib
from pathlib import Path

import tomli_w

from app.mapper import BOOL_FLAGS, LIST_FIELDS, state_from_dict, state_to_dict
from app.models import FilterDiff, FiltersState

FILTERS_FILE = Path("filters.toml")
LOCK_FILE = Path("filters.lock.toml")


def read_filters(path: Path = FILTERS_FILE) -> FiltersState:
    """Читает filters.toml → FiltersState. Raises FileNotFoundError если нет файла."""
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
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


def diff_states(old: FiltersState, new: FiltersState) -> FilterDiff:
    """Сравнивает два состояния, возвращает diff."""
    old_by_id = {f.id: f for f in old.filters}
    new_by_id = {f.id: f for f in new.filters}
    old_ids = set(old_by_id)
    new_ids = set(new_by_id)

    created = [new_by_id[fid] for fid in new_ids - old_ids]
    deleted = [old_by_id[fid] for fid in old_ids - new_ids]
    updated = [
        (old_by_id[fid], new_by_id[fid])
        for fid in old_ids & new_ids
        if old_by_id[fid] != new_by_id[fid]
    ]
    return FilterDiff(created=created, updated=updated, deleted=deleted)


def format_diff(diff: FilterDiff) -> str:
    """Форматирует FilterDiff в читаемый текст для вывода пользователю."""
    lines: list[str] = []
    for spec in diff.created:
        lines.append(f"  + [{spec.id}] {spec.title}")
    for old, new in diff.updated:
        lines.append(f"  ~ [{old.id}] {old.title}")
        for field in ("title", *LIST_FIELDS, *BOOL_FLAGS):
            ov, nv = getattr(old, field), getattr(new, field)
            if ov != nv:
                lines.append(f"      {field}: {ov!r} → {nv!r}")
    for spec in diff.deleted:
        lines.append(f"  - [{spec.id}] {spec.title}")
    return "\n".join(lines)
