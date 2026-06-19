from pathlib import Path

import pytest

from app.models import FilterSpec, FiltersState
from app.storage import (
    diff_states,
    format_diff,
    read_filters,
    read_lock,
    write_filters,
    write_lock,
)


def make_spec(fid: int, title: str = "Test", **kwargs) -> FilterSpec:
    return FilterSpec(id=fid, title=title, **kwargs)


def make_state(*specs: FilterSpec) -> FiltersState:
    return FiltersState(filters={s.id: s for s in specs})


# --- read_filters / write_filters ---


def test_write_read_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "filters.toml"
    state = make_state(
        make_spec(1, "Работа", channels=[123, 456], pinned=[111]),
        make_spec(2, "Мемы", broadcasts=True),
    )
    write_filters(state, path)
    assert read_filters(path) == state


def test_read_filters_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_filters(tmp_path / "nonexistent.toml")


def test_write_omits_empty_lists(tmp_path: Path) -> None:
    path = tmp_path / "filters.toml"
    write_filters(make_state(make_spec(1, "Empty")), path)
    content = path.read_text()
    assert "channels" not in content
    assert "pinned" not in content
    assert "exclude" not in content


def test_write_omits_false_flags(tmp_path: Path) -> None:
    path = tmp_path / "filters.toml"
    write_filters(make_state(make_spec(1, "NoFlags")), path)
    content = path.read_text()
    for flag in (
        "broadcasts",
        "contacts",
        "groups",
        "bots",
        "exclude_muted",
        "exclude_read",
        "exclude_archived",
    ):
        assert flag not in content


def test_write_includes_true_flags(tmp_path: Path) -> None:
    path = tmp_path / "filters.toml"
    spec = make_spec(1, "Channels", broadcasts=True, exclude_muted=True)
    write_filters(make_state(spec), path)
    content = path.read_text()
    assert "broadcasts = true" in content
    assert "exclude_muted = true" in content


def test_write_pinned_before_channels(tmp_path: Path) -> None:
    path = tmp_path / "filters.toml"
    spec = make_spec(1, "Ordered", channels=[10, 20], pinned=[5])
    write_filters(make_state(spec), path)
    content = path.read_text()
    assert content.index("pinned") < content.index("channels")


def test_write_filters_sorted_by_id(tmp_path: Path) -> None:
    path = tmp_path / "filters.toml"
    write_filters(
        make_state(make_spec(3, "C"), make_spec(1, "A"), make_spec(2, "B")), path
    )
    content = path.read_text()
    assert (
        content.index("[filters.1]")
        < content.index("[filters.2]")
        < content.index("[filters.3]")
    )


# --- read_lock / write_lock ---


def test_read_lock_missing_returns_none(tmp_path: Path) -> None:
    assert read_lock(tmp_path / "filters.lock.toml") is None


def test_write_read_lock_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "filters.lock.toml"
    state = make_state(make_spec(1, "Работа", channels=[42]))
    write_lock(state, path)
    assert read_lock(path) == state


# --- diff_states ---


def test_diff_identical_states_is_empty() -> None:
    state = make_state(make_spec(1, "A"), make_spec(2, "B"))
    diff = diff_states(state, state)
    assert diff.is_empty


def test_diff_detects_created() -> None:
    old = make_state(make_spec(1, "A"))
    new = make_state(make_spec(1, "A"), make_spec(2, "B"))
    diff = diff_states(old, new)
    assert len(diff.created) == 1
    assert diff.created[0].id == 2
    assert not diff.deleted
    assert not diff.updated


def test_diff_detects_deleted() -> None:
    old = make_state(make_spec(1, "A"), make_spec(2, "B"))
    new = make_state(make_spec(1, "A"))
    diff = diff_states(old, new)
    assert len(diff.deleted) == 1
    assert diff.deleted[0].id == 2
    assert not diff.created
    assert not diff.updated


def test_diff_detects_updated() -> None:
    old = make_state(make_spec(1, "Old Title"))
    new = make_state(make_spec(1, "New Title"))
    diff = diff_states(old, new)
    assert len(diff.updated) == 1
    old_spec, new_spec = diff.updated[0]
    assert old_spec.title == "Old Title"
    assert new_spec.title == "New Title"
    assert not diff.created
    assert not diff.deleted


def test_diff_all_change_types() -> None:
    old = make_state(
        make_spec(1, "Keep"), make_spec(2, "Delete"), make_spec(3, "Change")
    )
    new = make_state(make_spec(1, "Keep"), make_spec(3, "Changed"), make_spec(4, "New"))
    diff = diff_states(old, new)
    assert len(diff.created) == 1
    assert len(diff.deleted) == 1
    assert len(diff.updated) == 1


# --- format_diff ---


def test_format_diff_created() -> None:
    diff = diff_states(make_state(), make_state(make_spec(1, "Новый")))
    output = format_diff(diff)
    assert "  + [1] Новый" in output


def test_format_diff_deleted() -> None:
    diff = diff_states(make_state(make_spec(1, "Удалён")), make_state())
    output = format_diff(diff)
    assert "  - [1] Удалён" in output


def test_format_diff_updated_shows_changed_fields() -> None:
    old = make_state(make_spec(1, "A", channels=[10]))
    new = make_state(make_spec(1, "A", channels=[10, 20]))
    diff = diff_states(old, new)
    output = format_diff(diff)
    assert "  ~ [1] A" in output
    assert "channels" in output
    assert "[10]" in output
    assert "[10, 20]" in output


def test_format_diff_empty_is_empty_string() -> None:
    state = make_state(make_spec(1, "X"))
    assert format_diff(diff_states(state, state)) == ""
