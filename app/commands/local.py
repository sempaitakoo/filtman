from app.ops.filters import exclude_peers_from
from app.storage.diff import diff_states
from app.storage.io import read_filters, read_lock, write_filters


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


def cmd_exclude(target_id: int, source_id: int) -> None:
    try:
        old_state = read_filters()
    except FileNotFoundError:
        return

    try:
        new_state = exclude_peers_from(old_state, target_id, source_id)
    except ValueError:
        return

    diff = diff_states(old_state, new_state)
    if diff.is_empty:
        return

    answer = input("Применить? [y/N] ")
    if answer.strip().lower() != "y":
        return

    write_filters(new_state)
