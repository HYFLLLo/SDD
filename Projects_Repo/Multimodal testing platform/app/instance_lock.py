"""单实例互斥锁。

原实现靠"端口上 /api/config 返回 200"推断本平台是否已在运行，属启发式：
端口被别的服务占用、或本平台换了端口启动时都会误判。这里改为显式锁文件。

锁文件记录持有者 pid / port / 启动时间；退出时删除。进程异常退出会留下陈旧锁，
acquire() 会检测 pid 是否仍存活并自动接管，避免"崩溃后再也启动不了"。
"""
import json
import os
import sys
import time

try:
    import fcntl  # POSIX
except ImportError:  # pragma: no cover - Windows
    fcntl = None

try:
    import msvcrt  # Windows
except ImportError:  # pragma: no cover - POSIX
    msvcrt = None


class InstanceLock:
    """文件锁 + 独立的持有者信息文件。

    锁必须独占一个字节区域，Windows 下被锁的区域其他进程连读都读不到；
    因此持有者信息（pid / 端口）单独写一个 JSON 文件，只用于展示与陈旧检测，
    真正的互斥由锁文件保证。
    """

    def __init__(self, path):
        self.path = path
        self.info_path = os.path.join(
            os.path.dirname(path) or ".", os.path.basename(path) + ".json")
        self._fh = None
        self.info = {}

    # ---- 内部 ----
    def _read_info(self):
        try:
            with open(self.info_path, "r", encoding="utf-8") as fh:
                return json.load(fh) or {}
        except Exception:
            return {}

    def _write_info(self, info):
        payload = json.dumps(info, ensure_ascii=False)
        tmp = self.info_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.replace(tmp, self.info_path)

    @staticmethod
    def _pid_alive(pid):
        if not isinstance(pid, int) or pid <= 0:
            return False
        if pid == os.getpid():
            return True
        if os.name == "nt":
            try:
                import ctypes
                handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
                if not handle:
                    return False
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            except Exception:
                return False
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def _try_os_lock(self):
        """拿系统级排他锁；拿不到说明另一个进程真实持有。"""
        if msvcrt is not None:
            try:
                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
                return True
            except OSError:
                return False
        if fcntl is not None:
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except OSError:
                return False
        return True

    def _unlock(self):
        if self._fh is None:
            return
        try:
            if msvcrt is not None:
                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            elif fcntl is not None:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            self._fh.close()
        except Exception:
            pass
        self._fh = None

    # ---- 对外 ----
    def held(self):
        """只读探测：是否已有活跃实例。不会创建锁。"""
        info = self._read_info()
        if not info:
            return None
        if self._pid_alive(info.get("pid")):
            return info
        return None

    def acquire(self):
        """返回 (ok, info)。ok=False 时 info 为持锁实例信息。"""
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        info = self._read_info()
        if info and info.get("pid") != os.getpid() and self._pid_alive(info.get("pid")):
            return False, info

        self._fh = open(self.path, "a+b")
        if not self._try_os_lock():
            self._unlock()
            return False, info or {"pid": None}

        me = {"pid": os.getpid(), "started": time.strftime("%Y-%m-%d %H:%M:%S")}
        self._write_info(me)
        self.info = me
        return True, me

    def update(self, **kwargs):
        if not self.info:
            return
        self.info.update(kwargs)
        try:
            self._write_info(self.info)
        except Exception:
            pass

    def release(self):
        self._unlock()
        for target in (self.path, self.info_path):
            try:
                if os.path.exists(target):
                    os.remove(target)
            except Exception:
                pass
        self.info = {}
