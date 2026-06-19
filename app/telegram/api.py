# ruff: noqa: T201
import contextlib
from typing import cast

from hydrogram import Client, raw
from hydrogram.enums import ChatType

from app.models import (
    ChannelMatch,
    FilterSpec,
    FiltersState,
    PeerInfo,
    PeerUniverse,
)
from app.telegram.wrappers import (
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
        return [
            cid for p in peers if (cid := input_peer_to_chat_id(p)) is not None
        ]

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
    filters: list[FilterSpec] = [
        _raw_to_filter_spec(rf)
        for rf in raw_filters
        if not isinstance(rf, raw.types.DialogFilterDefault) and rf.id != 0
    ]
    return FiltersState(filters=filters)


async def apply_state(client: Client, target: FiltersState) -> None:
    """Применить FiltersState к Telegram: создать новые, обновить изменённые, удалить лишние."""
    current_raw = await fetch_filters(client)
    current_ids = {rf.id for rf in current_raw if rf.id != 0}
    target_ids = {spec.id for spec in target.filters}

    all_chat_ids: set[int] = set()
    for spec in target.filters:
        all_chat_ids.update(spec.channels)
        all_chat_ids.update(spec.pinned)
        all_chat_ids.update(spec.exclude)

    total = len(all_chat_ids)
    peers: dict[int, raw.base.InputPeer] = {}
    for i, cid in enumerate(all_chat_ids, 1):
        print(f"\rРезолвим пиры... {i}/{total}", end="", flush=True)        with contextlib.suppress(Exception):
            peers[cid] = await resolve_peer(client, cid)
    print()
    for spec in target.filters:
        print(f"  Обновляем [{spec.id}] {spec.title}")        raw_filter = _filter_spec_to_raw(spec, peers)
        await client.invoke(
            raw.functions.messages.UpdateDialogFilter(
                id=spec.id, filter=cast("raw.base.DialogFilter", raw_filter)
            )
        )

    for fid in current_ids - target_ids:
        await client.invoke(raw.functions.messages.UpdateDialogFilter(id=fid))

    order = [spec.id for spec in target.filters]
    await client.invoke(
        raw.functions.messages.UpdateDialogFiltersOrder(order=order)
    )


async def fetch_universe(client: Client) -> PeerUniverse:
    """Собирает метаданные всех диалогов пользователя в PeerUniverse."""
    peers: list[PeerInfo] = []
    async for dialog in iter_dialogs(client):
        chat = dialog.chat
        t = chat.type
        name = chat.title or getattr(chat, "full_name", None) or str(chat.id)
        is_contact = bool(getattr(chat, "is_contact", False))
        peers.append(
            PeerInfo(
                chat_id=chat.id,
                name=name,
                username=chat.username or None,
                is_broadcast=t == ChatType.CHANNEL,
                is_group=t in (ChatType.GROUP, ChatType.SUPERGROUP),
                is_contact=is_contact,
                is_non_contact=t == ChatType.PRIVATE and not is_contact,
                is_bot=t == ChatType.BOT,
            )
        )
        print(f"\rЗагружаем диалоги... {len(peers)}", end="", flush=True)    print()    return PeerUniverse(peers=peers)


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
