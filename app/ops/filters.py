import dataclasses

from app.models import FilterId, FiltersState


def exclude_peers_from(
    state: FiltersState, target_id: FilterId, source_id: FilterId
) -> FiltersState:
    target = next((f for f in state.filters if f.id == target_id), None)
    if target is None:
        msg = f"Фильтр {target_id} не найден"
        raise ValueError(msg)
    source = next((f for f in state.filters if f.id == source_id), None)
    if source is None:
        msg = f"Фильтр {source_id} не найден"
        raise ValueError(msg)

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
    return FiltersState(filters=new_filters)
