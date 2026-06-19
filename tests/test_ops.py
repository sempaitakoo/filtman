import pytest

from app.models import FilterSpec, FiltersState
from app.ops.filters import exclude_peers_from


def make_spec(fid: int, title: str = "Test", **kwargs) -> FilterSpec:
    return FilterSpec(id=fid, title=title, **kwargs)


def make_state(*specs: FilterSpec) -> FiltersState:
    return FiltersState(filters=list(specs))


def get(state: FiltersState, fid: int) -> FilterSpec:
    return next(f for f in state.filters if f.id == fid)


# --- exclude_peers_from ---


def test_source_channels_added_to_exclude() -> None:
    state = make_state(
        make_spec(1, "Target", channels=[10, 20]),
        make_spec(2, "Source", channels=[30, 40]),
    )
    result = get(exclude_peers_from(state, 1, 2), 1)
    assert 30 in result.exclude
    assert 40 in result.exclude


def test_source_pinned_added_to_exclude() -> None:
    state = make_state(
        make_spec(1, "Target"),
        make_spec(2, "Source", pinned=[99]),
    )
    result = get(exclude_peers_from(state, 1, 2), 1)
    assert 99 in result.exclude


def test_peers_removed_from_target_channels() -> None:
    state = make_state(
        make_spec(1, "Target", channels=[10, 30]),
        make_spec(2, "Source", channels=[30]),
    )
    result = get(exclude_peers_from(state, 1, 2), 1)
    assert 30 not in result.channels
    assert 10 in result.channels


def test_peers_removed_from_target_pinned() -> None:
    state = make_state(
        make_spec(1, "Target", pinned=[5], channels=[5, 10]),
        make_spec(2, "Source", channels=[5]),
    )
    result = get(exclude_peers_from(state, 1, 2), 1)
    assert 5 not in result.pinned
    assert 5 not in result.channels


def test_idempotent() -> None:
    state = make_state(
        make_spec(1, "Target", channels=[10]),
        make_spec(2, "Source", channels=[10]),
    )
    once = exclude_peers_from(state, 1, 2)
    twice = exclude_peers_from(once, 1, 2)
    assert get(once, 1).exclude == get(twice, 1).exclude


def test_empty_source_no_change() -> None:
    state = make_state(
        make_spec(1, "Target", channels=[10, 20]),
        make_spec(2, "Source"),
    )
    result = get(exclude_peers_from(state, 1, 2), 1)
    assert result.channels == [10, 20]
    assert result.exclude == []


def test_other_filters_unchanged() -> None:
    state = make_state(
        make_spec(1, "Target"),
        make_spec(2, "Source", channels=[5]),
        make_spec(3, "Other", channels=[5]),
    )
    result = exclude_peers_from(state, 1, 2)
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
    result = get(exclude_peers_from(state, 1, 2), 1)
    assert result.exclude == sorted(result.exclude)
