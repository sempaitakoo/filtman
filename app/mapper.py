from app.models import FilterSpec, FiltersState

BOOL_FLAGS = (
    "broadcasts",
    "contacts",
    "groups",
    "bots",
    "exclude_muted",
    "exclude_read",
    "exclude_archived",
)
LIST_FIELDS = ("pinned", "channels", "exclude")


def state_from_dict(data: dict) -> FiltersState:
    """Конвертирует распарсенный TOML-словарь в FiltersState."""
    filters: dict[int, FilterSpec] = {}
    for key, raw in data.get("filters", {}).items():
        fid = int(key)
        filters[fid] = FilterSpec(
            id=fid,
            title=raw["title"],
            channels=list(raw.get("channels", [])),
            pinned=list(raw.get("pinned", [])),
            exclude=list(raw.get("exclude", [])),
            broadcasts=bool(raw.get("broadcasts", False)),
            contacts=bool(raw.get("contacts", False)),
            groups=bool(raw.get("groups", False)),
            bots=bool(raw.get("bots", False)),
            exclude_muted=bool(raw.get("exclude_muted", False)),
            exclude_read=bool(raw.get("exclude_read", False)),
            exclude_archived=bool(raw.get("exclude_archived", False)),
        )
    return FiltersState(filters=filters)


def state_to_dict(state: FiltersState) -> dict:
    """Конвертирует FiltersState в TOML-совместимый словарь."""
    out: dict = {"filters": {}}
    for fid, spec in sorted(state.filters.items()):
        entry: dict = {"title": spec.title}
        if spec.pinned:
            entry["pinned"] = spec.pinned
        if spec.channels:
            entry["channels"] = spec.channels
        if spec.exclude:
            entry["exclude"] = spec.exclude
        for flag in BOOL_FLAGS:
            if getattr(spec, flag):
                entry[flag] = True
        out["filters"][str(fid)] = entry
    return out
