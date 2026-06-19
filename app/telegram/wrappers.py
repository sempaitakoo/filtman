from collections.abc import AsyncGenerator

from hydrogram import Client, raw
from hydrogram.raw.functions.messages import GetDialogFilters
from hydrogram.raw.types import DialogFilter
from hydrogram.types import Chat, Dialog
from hydrogram.utils import MAX_CHANNEL_ID


def input_peer_to_chat_id(peer: raw.base.InputPeer) -> int | None:
    if isinstance(peer, raw.types.InputPeerUser):
        return peer.user_id
    if isinstance(peer, raw.types.InputPeerChat):
        return -peer.chat_id
    if isinstance(peer, raw.types.InputPeerChannel):
        return MAX_CHANNEL_ID - peer.channel_id
    return None


def iter_dialogs(client: Client) -> AsyncGenerator[Dialog]:
    return client.get_dialogs()  # pyright: ignore[reportReturnType]


async def fetch_chat(client: Client, chat_id: int) -> Chat:
    return await client.get_chat(chat_id)  # pyright: ignore[reportReturnType]


async def resolve_peer(client: Client, chat_id: int) -> raw.base.InputPeer:
    return await client.resolve_peer(chat_id)  # pyright: ignore[reportReturnType]


async def fetch_filters(client: Client) -> list[DialogFilter]:
    response = await client.invoke(GetDialogFilters())
    return [f for f in response.filters if isinstance(f, DialogFilter)]
