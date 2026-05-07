"""File-based locking for shared writes across CC and OC."""
from __future__ import annotations
import contextlib
import os
import time
from pathlib import Path
from filelock import FileLock, Timeout as _Timeout


class FileLockTimeout(Exception):
    pass


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _maybe_clean_stale(lock_path: Path, stale_age_s: int):
    if not lock_path.exists():
        return
    age = time.time() - lock_path.stat().st_mtime
    if age < stale_age_s:
        return
    try:
        pid_str = lock_path.read_text().strip()
        if pid_str.isdigit() and _pid_alive(int(pid_str)):
            return
    except OSError:
        return
    try:
        lock_path.unlink()
    except OSError:
        pass


@contextlib.contextmanager
def shared_write(path: Path, *, timeout: float = 5.0, stale_age_s: int = 60, mode: str = "a"):
    """Acquire flock on `<path>.lock` then open `path` for append (default).

    Raises FileLockTimeout if can't acquire within `timeout` seconds.
    Auto-cleans stale locks (>stale_age_s old, PID dead).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    _maybe_clean_stale(lock_path, stale_age_s)
    lock = FileLock(str(lock_path), timeout=timeout)
    try:
        lock.acquire()
    except _Timeout as e:
        raise FileLockTimeout(f"could not acquire {lock_path} within {timeout}s") from e
    try:
        with open(path, mode) as f:
            try:
                lock_path.write_text(str(os.getpid()))
            except OSError:
                pass
            yield f
            f.flush()
            os.fsync(f.fileno())
    finally:
        lock.release()
