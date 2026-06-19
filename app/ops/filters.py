import dataclasses
from dataclasses import dataclass

from app.models import (
    ChatId,
    FilterId,
    FilterSpec,
    FiltersState,
    OverlapResult,
    PeerUniverse,
)

_INCLUSION_FLAGS: dict[str, str] = {
    "broadcasts": "is_broadcast",
    "groups": "is_group",
    "contacts": "is_contact",
    "non_contacts": "is_non_contact",
    "bots": "is_bot",
}
_DYNAMIC_EXCLUDE_FLAGS = ("exclude_muted", "exclude_read", "exclude_archived")


def resolve_filter(spec: FilterSpec, universe: PeerUniverse) -> set[ChatId]:
    """
    Материализует фильтр в конкретное множество chat_id используя universe.

    Inclusion-флаги (broadcasts, groups, ...) раскрываются через universe.
    Динамические exclude-флаги (exclude_muted/read/archived) не раскрываются —
    эти данные не кешируются в peers.lock.json, так как меняются постоянно.
    """
    result: set[ChatId] = set(spec.channels) | set(spec.pinned)

    for flag, attr in _INCLUSION_FLAGS.items():
        if getattr(spec, flag):
            result |= {p.chat_id for p in universe.peers if getattr(p, attr)}

    return result - set(spec.exclude)


def exclude_peers_from(
    state: FiltersState,
    target_id: FilterId,
    source_id: FilterId,
    universe: PeerUniverse | None = None,
) -> tuple[FiltersState, list[str]]:
    """
    Добавляет peers source-фильтра в exclude target-фильтра.

    Одновременно удаляет эти peers из channels и pinned target-фильтра.
    Возвращает (new_state, warnings) — warnings непустой если universe отсутствует
    при наличии флагов категорий, или source использует динамические exclude-флаги.
    """
    target = next((f for f in state.filters if f.id == target_id), None)
    if target is None:
        msg = f"Фильтр {target_id} не найден"
        raise ValueError(msg)
    source = next((f for f in state.filters if f.id == source_id), None)
    if source is None:
        msg = f"Фильтр {source_id} не найден"
        raise ValueError(msg)

    warnings: list[str] = []

    source_has_inclusion_flags = any(
        getattr(source, f) for f in _INCLUSION_FLAGS
    )
    if source_has_inclusion_flags and universe is None:
        warnings.append(
            f"Фильтр [{source_id}] использует флаги категорий "
            f"({', '.join(f for f in _INCLUSION_FLAGS if getattr(source, f))}), "
            "но peers.lock.json не найден. Выполните pull. "
            "Учтены только явные channels/pinned."
        )

    if any(getattr(source, f) for f in _DYNAMIC_EXCLUDE_FLAGS):
        active = [f for f in _DYNAMIC_EXCLUDE_FLAGS if getattr(source, f)]
        warnings.append(
            f"Фильтр [{source_id}] использует {', '.join(active)} — "
            "эти флаги не учитываются при материализации (динамические данные)."
        )

    if universe is not None:
        peers = resolve_filter(source, universe)
    else:
        peers = set(source.channels) | set(source.pinned)

    new_target = dataclasses.replace(
        target,
        exclude=sorted(set(target.exclude) | peers),
        channels=[c for c in target.channels if c not in peers],
        pinned=[c for c in target.pinned if c not in peers],
    )
    new_filters = [
        new_target if f.id == target_id else f for f in state.filters
    ]
    return FiltersState(filters=new_filters), warnings


@dataclass
class CompactSuggestion:
    flag: str
    peers: list[int]


def compact_filter(
    spec: FilterSpec, universe: PeerUniverse
) -> list[CompactSuggestion]:
    """Возвращает список предложений по замене явных channels на флаги категорий."""
    channels_set = set(spec.channels)
    suggestions: list[CompactSuggestion] = []
    for flag, attr in _INCLUSION_FLAGS.items():
        if getattr(spec, flag):
            continue
        category_peers = [p.chat_id for p in universe.peers if getattr(p, attr)]
        if category_peers and set(category_peers).issubset(channels_set):
            suggestions.append(
                CompactSuggestion(flag=flag, peers=category_peers)
            )
    return suggestions


def apply_compact(
    spec: FilterSpec, suggestions: list[CompactSuggestion]
) -> FilterSpec:
    """Устанавливает флаги и убирает соответствующие ids из channels."""
    to_remove: set[int] = set()
    overrides: dict[str, bool] = {}
    for s in suggestions:
        overrides[s.flag] = True
        to_remove.update(s.peers)
    return dataclasses.replace(
        spec,
        channels=[c for c in spec.channels if c not in to_remove],
        **overrides,
    )


def find_overlaps(
    state: FiltersState,
    universe: PeerUniverse,
    filter_id: FilterId | None = None,
) -> list[OverlapResult]:
    """Находит чаты, присутствующие в нескольких фильтрах одновременно."""
    chat_to_filters: dict[ChatId, list[FilterSpec]] = {}
    for f in state.filters:
        for chat_id in resolve_filter(f, universe):
            chat_to_filters.setdefault(chat_id, []).append(f)

    results = [
        OverlapResult(chat_id=chat_id, filters=filters)
        for chat_id, filters in chat_to_filters.items()
        if len(filters) >= 2  # noqa: PLR2004
    ]

    if filter_id is not None:
        results = [
            r for r in results if any(f.id == filter_id for f in r.filters)
        ]

    return sorted(results, key=lambda r: len(r.filters), reverse=True)
