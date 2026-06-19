import pytest

from app.models import FilterSpec, FiltersState, PeerInfo, PeerUniverse
from app.ops.filters import (
    apply_compact,
    compact_filter,
    exclude_peers_from,
    resolve_filter,
)


def make_spec(fid: int, title: str = "Test", **kwargs) -> FilterSpec:
    return FilterSpec(id=fid, title=title, **kwargs)


def make_state(*specs: FilterSpec) -> FiltersState:
    return FiltersState(filters=list(specs))


def make_peer(  # noqa: PLR0913
    chat_id: int,
    *,
    is_broadcast: bool = False,
    is_group: bool = False,
    is_contact: bool = False,
    is_non_contact: bool = False,
    is_bot: bool = False,
) -> PeerInfo:
    return PeerInfo(
        chat_id=chat_id,
        name=f"Chat {chat_id}",
        username=None,
        is_broadcast=is_broadcast,
        is_group=is_group,
        is_contact=is_contact,
        is_non_contact=is_non_contact,
        is_bot=is_bot,
    )


def make_universe(*peers: PeerInfo) -> PeerUniverse:
    return PeerUniverse(peers=list(peers))


def get(state: FiltersState, fid: int) -> FilterSpec:
    return next(f for f in state.filters if f.id == fid)


def do_exclude(
    state: FiltersState,
    target_id: int,
    source_id: int,
    universe: PeerUniverse | None = None,
) -> FiltersState:
    """Вспомогательная: распаковывает tuple, возвращает только FiltersState."""
    new_state, _ = exclude_peers_from(state, target_id, source_id, universe)
    return new_state


# --- resolve_filter ---


def test_resolve_explicit_channels() -> None:
    universe = make_universe(
        make_peer(1, is_broadcast=True), make_peer(2, is_group=True)
    )
    spec = make_spec(1, channels=[1, 2])
    assert resolve_filter(spec, universe) == {1, 2}


def test_resolve_broadcasts_flag() -> None:
    universe = make_universe(
        make_peer(1, is_broadcast=True),
        make_peer(2, is_group=True),
        make_peer(3, is_broadcast=True),
    )
    spec = make_spec(1, broadcasts=True)
    assert resolve_filter(spec, universe) == {1, 3}


def test_resolve_groups_flag() -> None:
    universe = make_universe(
        make_peer(1, is_broadcast=True),
        make_peer(2, is_group=True),
        make_peer(3, is_group=True),
    )
    spec = make_spec(1, groups=True)
    assert resolve_filter(spec, universe) == {2, 3}


def test_resolve_contacts_flag() -> None:
    universe = make_universe(
        make_peer(1, is_contact=True),
        make_peer(2, is_non_contact=True),
    )
    spec = make_spec(1, contacts=True)
    assert resolve_filter(spec, universe) == {1}


def test_resolve_non_contacts_flag() -> None:
    universe = make_universe(
        make_peer(1, is_contact=True),
        make_peer(2, is_non_contact=True),
    )
    spec = make_spec(1, non_contacts=True)
    assert resolve_filter(spec, universe) == {2}


def test_resolve_bots_flag() -> None:
    universe = make_universe(
        make_peer(1, is_bot=True), make_peer(2, is_broadcast=True)
    )
    spec = make_spec(1, bots=True)
    assert resolve_filter(spec, universe) == {1}


def test_resolve_flags_combined_with_channels() -> None:
    universe = make_universe(
        make_peer(10, is_broadcast=True), make_peer(20, is_group=True)
    )
    spec = make_spec(1, channels=[20], broadcasts=True)
    assert resolve_filter(spec, universe) == {10, 20}


def test_resolve_explicit_exclude_subtracted() -> None:
    universe = make_universe(
        make_peer(1, is_broadcast=True),
        make_peer(2, is_broadcast=True),
    )
    spec = make_spec(1, broadcasts=True, exclude=[2])
    assert resolve_filter(spec, universe) == {1}


def test_resolve_pinned_included() -> None:
    universe = make_universe(make_peer(1, is_broadcast=True))
    spec = make_spec(1, pinned=[99])
    assert resolve_filter(spec, universe) == {99}


def test_resolve_empty_universe() -> None:
    universe = make_universe()
    spec = make_spec(1, broadcasts=True, groups=True)
    assert resolve_filter(spec, universe) == set()


# --- exclude_peers_from: поведение без universe ---


def test_source_channels_added_to_exclude() -> None:
    state = make_state(
        make_spec(1, "Target", channels=[10, 20]),
        make_spec(2, "Source", channels=[30, 40]),
    )
    result = get(do_exclude(state, 1, 2), 1)
    assert 30 in result.exclude
    assert 40 in result.exclude


def test_source_pinned_added_to_exclude() -> None:
    state = make_state(
        make_spec(1, "Target"),
        make_spec(2, "Source", pinned=[99]),
    )
    result = get(do_exclude(state, 1, 2), 1)
    assert 99 in result.exclude


def test_peers_removed_from_target_channels() -> None:
    state = make_state(
        make_spec(1, "Target", channels=[10, 30]),
        make_spec(2, "Source", channels=[30]),
    )
    result = get(do_exclude(state, 1, 2), 1)
    assert 30 not in result.channels
    assert 10 in result.channels


def test_peers_removed_from_target_pinned() -> None:
    state = make_state(
        make_spec(1, "Target", pinned=[5], channels=[5, 10]),
        make_spec(2, "Source", channels=[5]),
    )
    result = get(do_exclude(state, 1, 2), 1)
    assert 5 not in result.pinned
    assert 5 not in result.channels


def test_idempotent() -> None:
    state = make_state(
        make_spec(1, "Target", channels=[10]),
        make_spec(2, "Source", channels=[10]),
    )
    once = do_exclude(state, 1, 2)
    twice = do_exclude(once, 1, 2)
    assert get(once, 1).exclude == get(twice, 1).exclude


def test_empty_source_no_change() -> None:
    state = make_state(
        make_spec(1, "Target", channels=[10, 20]),
        make_spec(2, "Source"),
    )
    result = get(do_exclude(state, 1, 2), 1)
    assert result.channels == [10, 20]
    assert result.exclude == []


def test_other_filters_unchanged() -> None:
    state = make_state(
        make_spec(1, "Target"),
        make_spec(2, "Source", channels=[5]),
        make_spec(3, "Other", channels=[5]),
    )
    result = do_exclude(state, 1, 2)
    assert get(result, 3) == get(state, 3)


def test_missing_target_raises() -> None:
    state = make_state(make_spec(2, "Source"))
    with pytest.raises(ValueError, match="99"):
        exclude_peers_from(state, 99, 2)


def test_missing_source_raises() -> None:
    state = make_state(make_spec(1, "Target"))
    with pytest.raises(ValueError, match="99"):
        exclude_peers_from(state, 1, 99)


def test_exclude_list_sorted() -> None:
    state = make_state(
        make_spec(1, "Target", exclude=[50]),
        make_spec(2, "Source", channels=[10, 30]),
    )
    result = get(do_exclude(state, 1, 2), 1)
    assert result.exclude == sorted(result.exclude)


# --- exclude_peers_from: с universe ---


def test_with_universe_broadcasts_expanded() -> None:
    universe = make_universe(
        make_peer(1, is_broadcast=True),
        make_peer(2, is_group=True),
        make_peer(3, is_broadcast=True),
    )
    state = make_state(
        make_spec(1, "Target", channels=[1, 2, 10]),
        make_spec(2, "Каналы", broadcasts=True),
    )
    result = get(do_exclude(state, 1, 2, universe), 1)
    assert set(result.exclude) == {1, 3}
    assert result.channels == [2, 10]


def test_with_universe_no_warnings_when_flags_present() -> None:
    universe = make_universe(make_peer(1, is_broadcast=True))
    state = make_state(
        make_spec(1, "Target"),
        make_spec(2, "Source", broadcasts=True),
    )
    _, warnings = exclude_peers_from(state, 1, 2, universe)
    assert warnings == []


def test_without_universe_warns_when_source_has_flags() -> None:
    state = make_state(
        make_spec(1, "Target"),
        make_spec(2, "Source", broadcasts=True),
    )
    _, warnings = exclude_peers_from(state, 1, 2, universe=None)
    assert len(warnings) == 1
    assert "peers.lock.json" in warnings[0]
    assert "broadcasts" in warnings[0]


def test_without_universe_no_warning_when_source_has_no_flags() -> None:
    state = make_state(
        make_spec(1, "Target"),
        make_spec(2, "Source", channels=[5, 6]),
    )
    _, warnings = exclude_peers_from(state, 1, 2, universe=None)
    assert warnings == []


def test_dynamic_exclude_flags_produce_warning() -> None:
    universe = make_universe(make_peer(1, is_broadcast=True))
    state = make_state(
        make_spec(1, "Target"),
        make_spec(2, "Source", broadcasts=True, exclude_muted=True),
    )
    _, warnings = exclude_peers_from(state, 1, 2, universe)
    assert any("exclude_muted" in w for w in warnings)


def test_with_universe_groups_flag() -> None:
    universe = make_universe(
        make_peer(10, is_group=True),
        make_peer(20, is_group=True),
        make_peer(30, is_broadcast=True),
    )
    state = make_state(
        make_spec(1, "Target", channels=[10, 20, 30, 40]),
        make_spec(2, "Группы", groups=True),
    )
    result = get(do_exclude(state, 1, 2, universe), 1)
    assert set(result.exclude) == {10, 20}
    assert result.channels == [30, 40]


# --- compact_filter ---


def test_compact_suggests_broadcasts_when_all_present() -> None:
    universe = make_universe(
        make_peer(1, is_broadcast=True),
        make_peer(2, is_broadcast=True),
        make_peer(3, is_group=True),
    )
    spec = make_spec(1, channels=[1, 2])
    suggestions = compact_filter(spec, universe)
    flags = {s.flag for s in suggestions}
    assert "broadcasts" in flags
    assert "groups" not in flags


def test_compact_no_suggestion_when_partial_match() -> None:
    universe = make_universe(
        make_peer(1, is_broadcast=True),
        make_peer(2, is_broadcast=True),
    )
    spec = make_spec(1, channels=[1])  # только половина broadcasts
    suggestions = compact_filter(spec, universe)
    assert all(s.flag != "broadcasts" for s in suggestions)


def test_compact_no_suggestion_when_flag_already_set() -> None:
    universe = make_universe(make_peer(1, is_broadcast=True))
    spec = make_spec(1, channels=[1], broadcasts=True)
    suggestions = compact_filter(spec, universe)
    assert all(s.flag != "broadcasts" for s in suggestions)


def test_compact_multiple_flags_suggested() -> None:
    universe = make_universe(
        make_peer(1, is_broadcast=True),
        make_peer(2, is_group=True),
    )
    spec = make_spec(1, channels=[1, 2])
    suggestions = compact_filter(spec, universe)
    flags = {s.flag for s in suggestions}
    assert flags == {"broadcasts", "groups"}


def test_compact_empty_category_no_suggestion() -> None:
    universe = make_universe(make_peer(1, is_group=True))
    spec = make_spec(1, channels=[1])
    # broadcasts категория пустая → не предлагаем broadcasts=true
    suggestions = compact_filter(spec, universe)
    assert all(s.flag != "broadcasts" for s in suggestions)


def test_compact_peers_list_correct() -> None:
    universe = make_universe(
        make_peer(10, is_broadcast=True),
        make_peer(20, is_broadcast=True),
    )
    spec = make_spec(1, channels=[10, 20])
    (suggestion,) = compact_filter(spec, universe)
    assert suggestion.flag == "broadcasts"
    assert set(suggestion.peers) == {10, 20}


def test_compact_empty_channels_no_suggestions() -> None:
    universe = make_universe(make_peer(1, is_broadcast=True))
    spec = make_spec(1)
    assert compact_filter(spec, universe) == []


def test_compact_empty_universe_no_suggestions() -> None:
    spec = make_spec(1, channels=[1, 2])
    assert compact_filter(spec, make_universe()) == []


# --- apply_compact ---


def test_apply_compact_sets_flag() -> None:
    universe = make_universe(make_peer(1, is_broadcast=True))
    spec = make_spec(1, channels=[1])
    suggestions = compact_filter(spec, universe)
    result = apply_compact(spec, suggestions)
    assert result.broadcasts is True


def test_apply_compact_removes_peers_from_channels() -> None:
    universe = make_universe(
        make_peer(1, is_broadcast=True),
        make_peer(2, is_broadcast=True),
    )
    spec = make_spec(1, channels=[1, 2, 99])
    suggestions = compact_filter(spec, universe)
    result = apply_compact(spec, suggestions)
    assert result.channels == [99]
    assert 1 not in result.channels
    assert 2 not in result.channels


def test_apply_compact_preserves_other_fields() -> None:
    universe = make_universe(make_peer(1, is_broadcast=True))
    spec = make_spec(1, title="Keep", channels=[1], pinned=[5], exclude=[9])
    suggestions = compact_filter(spec, universe)
    result = apply_compact(spec, suggestions)
    assert result.title == "Keep"
    assert result.pinned == [5]
    assert result.exclude == [9]


def test_apply_compact_multiple_suggestions() -> None:
    universe = make_universe(
        make_peer(1, is_broadcast=True),
        make_peer(2, is_group=True),
    )
    spec = make_spec(1, channels=[1, 2, 99])
    suggestions = compact_filter(spec, universe)
    result = apply_compact(spec, suggestions)
    assert result.broadcasts is True
    assert result.groups is True
    assert result.channels == [99]


def test_apply_compact_does_not_mutate_original() -> None:
    universe = make_universe(make_peer(1, is_broadcast=True))
    spec = make_spec(1, channels=[1])
    suggestions = compact_filter(spec, universe)
    apply_compact(spec, suggestions)
    assert spec.broadcasts is False
    assert spec.channels == [1]
