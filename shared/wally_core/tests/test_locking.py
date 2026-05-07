import multiprocessing
import os
import time
from pathlib import Path
import pytest
from wally_core.locking import shared_write, FileLockTimeout


def _writer(path_str, payload, delay=0):
    with shared_write(Path(path_str), timeout=2) as f:
        if delay:
            time.sleep(delay)
        f.write(payload)


def test_shared_write_serializes_concurrent_writes(tmp_path):
    target = tmp_path / "log.csv"
    procs = [
        multiprocessing.Process(target=_writer, args=(str(target), f"row{i}\n"))
        for i in range(5)
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    content = target.read_text()
    assert content.count("\n") == 5


def test_shared_write_timeout_when_held(tmp_path):
    target = tmp_path / "log.csv"
    blocker = multiprocessing.Process(target=_writer, args=(str(target), "blocker\n", 3))
    blocker.start()
    time.sleep(0.5)
    with pytest.raises(FileLockTimeout):
        with shared_write(target, timeout=1):
            pass
    blocker.join()


def test_stale_lock_cleanup(tmp_path):
    target = tmp_path / "log.csv"
    lock_file = tmp_path / "log.csv.lock"
    lock_file.write_text("999999")
    with shared_write(target, timeout=1, stale_age_s=0) as f:
        f.write("ok\n")
    assert target.read_text() == "ok\n"
