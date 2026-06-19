from typing import cast

from hydrogram import raw
from hydrogram.utils import MAX_CHANNEL_ID

from app.telegram.wrappers import input_peer_to_chat_id


def _peer(obj: object) -> raw.base.InputPeer:
    return cast("raw.base.InputPeer", obj)


def test_user_peer_returns_user_id() -> None:
    assert (
        input_peer_to_chat_id(
            _peer(raw.types.InputPeerUser(user_id=42, access_hash=0))
        )
        == 42
    )


def test_chat_peer_returns_negative_chat_id() -> None:
    assert (
        input_peer_to_chat_id(_peer(raw.types.InputPeerChat(chat_id=100)))
        == -100
    )


def test_channel_peer_returns_correct_id() -> None:
    assert (
        input_peer_to_chat_id(
            _peer(raw.types.InputPeerChannel(channel_id=999, access_hash=0))
        )
        == MAX_CHANNEL_ID - 999
    )


def test_unknown_peer_returns_none() -> None:
    assert input_peer_to_chat_id(_peer(raw.types.InputPeerEmpty())) is None


def test_user_id_zero() -> None:
    assert (
        input_peer_to_chat_id(
            _peer(raw.types.InputPeerUser(user_id=0, access_hash=0))
        )
        == 0
    )


def test_chat_id_is_always_negative() -> None:
    result = input_peer_to_chat_id(_peer(raw.types.InputPeerChat(chat_id=1)))
    assert result is not None
    assert result < 0


def test_channel_id_is_always_negative() -> None:
    result = input_peer_to_chat_id(
        _peer(raw.types.InputPeerChannel(channel_id=1, access_hash=0))
    )
    assert result is not None
    assert result < 0
