from app.mapper import BOOL_FLAGS, state_from_dict, state_to_dict
from app.models import FilterSpec, FiltersState


def make_spec(fid: int, title: str = "Test", **kwargs) -> FilterSpec:
    return FilterSpec(id=fid, title=title, **kwargs)


def make_state(*specs: FilterSpec) -> FiltersState:
    return FiltersState(filters={s.id: s for s in specs})


# --- state_from_dict ---


def test_from_dict_empty_data() -> None:
    assert state_from_dict({}) == FiltersState(filters={})


def test_from_dict_empty_filters_section() -> None:
    assert state_from_dict({"filters": {}}) == FiltersState(filters={})


def test_from_dict_parses_title() -> None:
    state = state_from_dict({"filters": {"1": {"title": "Работа"}}})
    assert state.filters[1].title == "Работа"


def test_from_dict_parses_channels_pinned_exclude() -> None:
    state = state_from_dict(
        {
            "filters": {
                "1": {
                    "title": "T",
                    "channels": [10, 20],
                    "pinned": [5],
                    "exclude": [99],
                },
            }
        }
    )
    spec = state.filters[1]
    assert spec.channels == [10, 20]
    assert spec.pinned == [5]
    assert spec.exclude == [99]


def test_from_dict_defaults_lists_to_empty() -> None:
    state = state_from_dict({"filters": {"1": {"title": "T"}}})
    spec = state.filters[1]
    assert spec.channels == []
    assert spec.pinned == []
    assert spec.exclude == []


def test_from_dict_parses_true_flags() -> None:
    raw = {
        "title": "T",
        "broadcasts": True,
        "contacts": True,
        "groups": True,
        "bots": True,
        "exclude_muted": True,
        "exclude_read": True,
        "exclude_archived": True,
    }
    state = state_from_dict({"filters": {"1": raw}})
    spec = state.filters[1]
    for flag in BOOL_FLAGS:
        assert getattr(spec, flag) is True, flag


def test_from_dict_defaults_flags_to_false() -> None:
    state = state_from_dict({"filters": {"1": {"title": "T"}}})
    spec = state.filters[1]
    for flag in BOOL_FLAGS:
        assert getattr(spec, flag) is False, flag


def test_from_dict_parses_string_keys_as_int() -> None:
    state = state_from_dict({"filters": {"42": {"title": "T"}}})
    assert 42 in state.filters
    assert state.filters[42].id == 42


def test_from_dict_multiple_filters() -> None:
    state = state_from_dict(
        {
            "filters": {
                "1": {"title": "A"},
                "2": {"title": "B"},
            }
        }
    )
    assert set(state.filters.keys()) == {1, 2}


# --- state_to_dict ---


def test_to_dict_empty_state() -> None:
    result = state_to_dict(FiltersState(filters={}))
    assert result == {"filters": {}}


def test_to_dict_includes_title() -> None:
    result = state_to_dict(make_state(make_spec(1, "Работа")))
    assert result["filters"]["1"]["title"] == "Работа"


def test_to_dict_omits_empty_lists() -> None:
    result = state_to_dict(make_state(make_spec(1, "T")))
    entry = result["filters"]["1"]
    assert "channels" not in entry
    assert "pinned" not in entry
    assert "exclude" not in entry


def test_to_dict_omits_false_flags() -> None:
    result = state_to_dict(make_state(make_spec(1, "T")))
    entry = result["filters"]["1"]
    for flag in BOOL_FLAGS:
        assert flag not in entry, flag


def test_to_dict_includes_nonempty_lists() -> None:
    spec = make_spec(1, "T", channels=[10, 20], pinned=[5], exclude=[99])
    result = state_to_dict(make_state(spec))
    entry = result["filters"]["1"]
    assert entry["channels"] == [10, 20]
    assert entry["pinned"] == [5]
    assert entry["exclude"] == [99]


def test_to_dict_includes_true_flags() -> None:
    spec = make_spec(1, "T", broadcasts=True, exclude_muted=True)
    result = state_to_dict(make_state(spec))
    entry = result["filters"]["1"]
    assert entry["broadcasts"] is True
    assert entry["exclude_muted"] is True


def test_to_dict_uses_string_keys() -> None:
    result = state_to_dict(make_state(make_spec(7, "T")))
    assert "7" in result["filters"]


def test_to_dict_sorts_by_id() -> None:
    state = make_state(make_spec(3, "C"), make_spec(1, "A"), make_spec(2, "B"))
    keys = list(state_to_dict(state)["filters"].keys())
    assert keys == ["1", "2", "3"]


# --- roundtrip ---


def test_roundtrip_preserves_all_fields() -> None:
    spec = FilterSpec(
        id=5,
        title="Full",
        channels=[1, 2, 3],
        pinned=[10],
        exclude=[99],
        broadcasts=True,
        contacts=False,
        groups=True,
        bots=False,
        exclude_muted=True,
        exclude_read=False,
        exclude_archived=True,
    )
    state = make_state(spec)
    assert state_from_dict(state_to_dict(state)) == state
