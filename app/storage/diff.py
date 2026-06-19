from app.mapper import BOOL_FLAGS, LIST_FIELDS
from app.models import FilterDiff, FiltersState


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


_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_RESET = "\033[0m"


def format_diff(diff: FilterDiff, *, colored: bool = False) -> str:
    """Форматирует FilterDiff в читаемый текст для вывода пользователю."""

    def c(color: str, text: str) -> str:
        return f"{color}{text}{_RESET}" if colored else text

    lines: list[str] = [
        c(_GREEN, f"  + [{spec.id}] {spec.title}") for spec in diff.created
    ]
    for old, new in diff.updated:
        lines.append(c(_YELLOW, f"  ~ [{old.id}] {old.title}"))
        for field in ("title", *LIST_FIELDS, *BOOL_FLAGS):
            ov, nv = getattr(old, field), getattr(new, field)
            if ov != nv:
                lines.append(c(_YELLOW, f"      {field}: {ov!r} → {nv!r}"))
    lines.extend(
        c(_RED, f"  - [{spec.id}] {spec.title}") for spec in diff.deleted
    )
    return "\n".join(lines)
