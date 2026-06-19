from app.storage.diff import diff_states
from app.storage.io import read_filters, read_lock


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
