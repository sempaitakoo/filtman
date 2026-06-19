# ruff: noqa: T201
from app.ops.filters import (
    CompactSuggestion,
    apply_compact,
    compact_filter,
    exclude_peers_from,
    find_overlaps,
)
from app.storage.diff import diff_states, format_diff
from app.storage.io import read_filters, read_lock, write_filters
from app.storage.peers import read_universe


def cmd_diff() -> None:
    try:
        local_state = read_filters()
    except FileNotFoundError:
        return

    lock_state = read_lock()
    if lock_state is None:
        return

    diff = diff_states(lock_state, local_state)
    if diff.is_empty:
        return

    print(format_diff(diff, colored=True))


def cmd_exclude(target_id: int, source_id: int) -> None:
    try:
        old_state = read_filters()
    except FileNotFoundError:
        return

    universe = read_universe()

    try:
        new_state, warnings = exclude_peers_from(
            old_state, target_id, source_id, universe
        )
    except ValueError:
        return

    for w in warnings:
        print(f"Предупреждение: {w}")
    diff = diff_states(old_state, new_state)
    if diff.is_empty:
        print("Нет изменений.")
        return

    print(format_diff(diff, colored=True))
    answer = input("Применить? [y/N] ")
    if answer.strip().lower() != "y":
        return

    write_filters(new_state, universe=universe)


def _format_suggestions(suggestions: list[CompactSuggestion]) -> str:
    return "\n".join(
        f"  {s.flag}=true заменяет {len(s.peers)} явных peers"
        for s in suggestions
    )


def cmd_compact(filter_id: int | None = None) -> None:
    try:
        state = read_filters()
    except FileNotFoundError:
        print("filters.toml не найден.")
        return

    universe = read_universe()
    if universe is None:
        print("peers.lock.json не найден. Выполните pull.")
        return

    if filter_id is not None:
        spec = next((f for f in state.filters if f.id == filter_id), None)
        if spec is None:
            print(f"Фильтр {filter_id} не найден.")
            return
        suggestions = compact_filter(spec, universe)
        if not suggestions:
            print(f"Нет предложений для фильтра {filter_id}.")
            return
        print(f"[{spec.id}] {spec.title}")
        print(_format_suggestions(suggestions))
        print("! Флаги включают будущие чаты этих категорий автоматически.")
        answer = input("Применить? [y/N] ")
        if answer.strip().lower() != "y":
            return
        new_spec = apply_compact(spec, suggestions)
        new_filters = [
            new_spec if f.id == filter_id else f for f in state.filters
        ]
        write_filters(state.__class__(filters=new_filters), universe=universe)
    else:
        any_found = False
        for spec in state.filters:
            suggestions = compact_filter(spec, universe)
            if suggestions:
                any_found = True
                print(f"[{spec.id}] {spec.title}")
                print(_format_suggestions(suggestions))
                print()
        if not any_found:
            print("Нет предложений.")


def cmd_overlap(filter_id: int | None = None) -> None:
    try:
        state = read_filters()
    except FileNotFoundError:
        print("filters.toml не найден.")
        return

    if filter_id is not None:
        anchor = next((f for f in state.filters if f.id == filter_id), None)
        if anchor is None:
            print(f"Фильтр {filter_id} не найден.")
            return

    universe = read_universe()
    if universe is None:
        print("peers.lock.json не найден. Выполните pull.")
        return

    results = find_overlaps(state, universe, filter_id)
    if not results:
        print("Дублей нет.")
        return

    max_len = max(len(str(r.chat_id)) for r in results)

    if filter_id is None:
        for r in results:
            folders = "  ".join(f"[{f.id}] {f.title}" for f in r.filters)
            count = len(r.filters)
            print(
                f"{str(r.chat_id).ljust(max_len)}  в {count} папках: {folders}"
            )
    else:
        anchor_title = next(f.title for f in state.filters if f.id == filter_id)
        for r in results:
            others = "  ".join(
                f"[{f.id}] {f.title}" for f in r.filters if f.id != filter_id
            )
            print(f"{str(r.chat_id).ljust(max_len)}  также в: {others}")
        print()
        print(
            f"{len(results)} чат{'а' if len(results) in (2, 3, 4) else 'ов'} "
            f"из [{filter_id}] {anchor_title} присутствуют в других папках."
        )


def cmd_annotate() -> None:
    try:
        state = read_filters()
    except FileNotFoundError:
        print("filters.toml не найден.")
        return

    universe = read_universe()
    if universe is None:
        print("peers.lock.json не найден. Выполните pull.")
        return

    write_filters(state, universe=universe)
    print("filters.toml обновлён с комментариями.")
