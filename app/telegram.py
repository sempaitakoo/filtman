from typing import cast

from hydrogram import Client, raw

from app.models import ChannelMatch, FilterSpec, FiltersState
from app.wrappers import (
    fetch_filters,
    input_peer_to_chat_id,
    iter_dialogs,
    resolve_peer,
)

_BOOL_FLAGS = (
    "broadcasts",
    "contacts",
    "non_contacts",
    "groups",
    "bots",
    "exclude_muted",
    "exclude_read",
    "exclude_archived",
)


def _raw_to_filter_spec(raw_filter: raw.types.DialogFilter) -> FilterSpec:
    def peers_to_ids(peers: list[raw.base.InputPeer]) -> list[int]:
        return [cid for p in peers if (cid := input_peer_to_chat_id(p)) is not None]

    return FilterSpec(
        id=raw_filter.id,
        title=raw_filter.title,
        channels=peers_to_ids(raw_filter.include_peers),
        pinned=peers_to_ids(raw_filter.pinned_peers),
        exclude=peers_to_ids(raw_filter.exclude_peers),
        broadcasts=bool(raw_filter.broadcasts),
        contacts=bool(raw_filter.contacts),
        non_contacts=bool(raw_filter.non_contacts),
        groups=bool(raw_filter.groups),
        bots=bool(raw_filter.bots),
        exclude_muted=bool(raw_filter.exclude_muted),
        exclude_read=bool(raw_filter.exclude_read),
        exclude_archived=bool(raw_filter.exclude_archived),
    )


def _filter_spec_to_raw(
    spec: FilterSpec, peers: dict[int, raw.base.InputPeer]
) -> raw.types.DialogFilter:
    def ids_to_peers(ids: list[int]) -> list[raw.base.InputPeer]:
        return [peers[cid] for cid in ids if cid in peers]

    return raw.types.DialogFilter(
        id=spec.id,
        title=spec.title,
        include_peers=ids_to_peers(spec.channels),
        pinned_peers=ids_to_peers(spec.pinned),
        exclude_peers=ids_to_peers(spec.exclude),
        broadcasts=spec.broadcasts or None,
        contacts=spec.contacts or None,
        non_contacts=spec.non_contacts or None,
        groups=spec.groups or None,
        bots=spec.bots or None,
        exclude_muted=spec.exclude_muted or None,
        exclude_read=spec.exclude_read or None,
        exclude_archived=spec.exclude_archived or None,
    )


async def fetch_state(client: Client) -> FiltersState:
    """Получить текущие фильтры из Telegram → FiltersState. Пропускает id=0 (All Chats)."""
    raw_filters = await fetch_filters(client)
    filters: dict[int, FilterSpec] = {}
    for rf in raw_filters:
        if rf.id == 0:
            continue
        spec = _raw_to_filter_spec(rf)
        filters[spec.id] = spec
    return FiltersState(filters=filters)


async def apply_state(client: Client, target: FiltersState) -> None:
    """Применить FiltersState к Telegram: создать новые, обновить изменённые, удалить лишние."""
    current_raw = await fetch_filters(client)
    current_ids = {rf.id for rf in current_raw if rf.id != 0}
    target_ids = set(target.filters)

    all_chat_ids: set[int] = set()
    for spec in target.filters.values():
        all_chat_ids.update(spec.channels)
        all_chat_ids.update(spec.pinned)
        all_chat_ids.update(spec.exclude)

    peers: dict[int, raw.base.InputPeer] = {}
    for cid in all_chat_ids:
        try:
            peers[cid] = await resolve_peer(client, cid)
        except Exception:
            pass

    for fid in target_ids:
        spec = target.filters[fid]
        raw_filter = _filter_spec_to_raw(spec, peers)
        await client.invoke(
            raw.functions.messages.UpdateDialogFilter(
                id=fid, filter=cast(raw.base.DialogFilter, raw_filter)
            )
        )

    for fid in current_ids - target_ids:
        await client.invoke(raw.functions.messages.UpdateDialogFilter(id=fid))


async def search_channels(client: Client, query: str) -> list[ChannelMatch]:
    """Искать среди диалогов пользователя по подстроке в title/username (case-insensitive)."""
    q = query.lower()
    matches: list[ChannelMatch] = []
    async for dialog in iter_dialogs(client):
        chat = dialog.chat
        title = chat.title or ""
        username = chat.username or ""
        if q in title.lower() or q in username.lower():
            matches.append(
                ChannelMatch(
                    chat_id=chat.id,
                    username=username or None,
                    title=title,
                )
            )
    return matches
