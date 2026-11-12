import json
import os
import time

import pytest

from app.instance_lock import InstanceLock


def _lock(tmp_path):
    return InstanceLock(str(tmp_path / "instance.lock"))


def test_acquire_writes_info_file(tmp_path):
    lock = _lock(tmp_path)
    ok, info = lock.acquire()
    try:
        assert ok is True
        assert info["pid"] == os.getpid()
        assert os.path.isfile(lock.info_path)
        with open(lock.info_path, "r", encoding="utf-8") as fh:
            assert json.load(fh)["pid"] == os.getpid()
    finally:
        lock.release()


def test_second_acquire_is_rejected_with_holder_info(tmp_path):
    first = _lock(tmp_path)
    second = _lock(tmp_path)
    assert first.acquire()[0] is True
    try:
        first.update(port=8821)
        ok, info = second.acquire()
        assert ok is False
        assert info["pid"] == os.getpid()
        assert info["port"] == 8821
    finally:
        first.release()


def test_release_allows_reacquire_and_removes_files(tmp_path):
    lock = _lock(tmp_path)
    assert lock.acquire()[0] is True
    lock.release()
    assert not os.path.exists(lock.path)
    assert not os.path.exists(lock.info_path)
    again = _lock(tmp_path)
    assert again.acquire()[0] is True
    again.release()


def test_stale_lock_with_dead_pid_is_taken_over(tmp_path):
    lock = _lock(tmp_path)
    os.makedirs(str(tmp_path), exist_ok=True)
    with open(lock.info_path, "w", encoding="utf-8") as fh:
        json.dump({"pid": 999999, "started": "2020-01-01 00:00:00", "port": 1}, fh)
    with open(lock.path, "wb") as fh:
        fh.write(b"\0" * 8)
    ok, info = lock.acquire()
    try:
        assert ok is True
        assert info["pid"] == os.getpid()
    finally:
        lock.release()


def test_held_reports_only_live_holder(tmp_path):
    lock = _lock(tmp_path)
    assert lock.held() is None
    with open(lock.info_path, "w", encoding="utf-8") as fh:
        json.dump({"pid": 999999}, fh)
    assert lock.held() is None
    with open(lock.info_path, "w", encoding="utf-8") as fh:
        json.dump({"pid": os.getpid(), "port": 8735}, fh)
    assert lock.held()["port"] == 8735


def test_update_is_noop_before_acquire(tmp_path):
    lock = _lock(tmp_path)
    lock.update(port=1234)
    assert not os.path.exists(lock.info_path)


def test_info_path_is_separate_from_lock(tmp_path):
    lock = _lock(tmp_path)
    assert lock.info_path.endswith("instance.lock.json")
    assert lock.info_path != lock.path


def test_packaged_lock_is_anchored_to_exe_dir():
    """打包后锁必须落在 exe 同级的 workspace，而不是 PyInstaller 临时解包目录。

    onefile 模式每次启动都会新建 _MEIxxxx，若锁跟着临时目录走，第二次双击
    会误判"没有实例在跑"，在 8736 再起一个实例，两个进程同时写同一份数据。
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "run.py"), encoding="utf-8") as fh:
        src = fh.read()
    assert "def _base_dir() -> str:" in src
    assert 'if getattr(sys, "frozen", False):' in src
    assert "return os.path.dirname(sys.executable)" in src
    assert 'os.path.join(_base_dir(), "workspace")' in src
    assert 'os.path.dirname(os.path.abspath(__file__)), "workspace"' not in src
