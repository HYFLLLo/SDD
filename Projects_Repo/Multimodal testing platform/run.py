"""启动入口：启动本地服务并自动打开浏览器

开发：python run.py
打包后：双击 多模态测试平台.exe

端口策略：
- 默认 8735；若已有本平台实例在运行，直接打开浏览器复用，不再启动第二个；
- 若被其他程序占用，自动顺延到下一个可用端口。

单实例判定使用 workspace/instance.lock（记录 pid + 端口），而非"端口上是不是本应用"的猜测：
进程异常退出留下的陈旧锁会被自动接管。
"""
import os
import socket
import sys
import threading
import time
import traceback
import webbrowser

# 无控制台打包（console=False）下 sys.stdout / sys.stderr 是 None：
# print()、traceback.print_exc()、logging.StreamHandler 都会直接抛 AttributeError，
# 把问题藏成"双击没反应"。必须在导入业务模块之前就重定向到空设备；
# 有没有真实控制台另存一个标志，供报错时决定用弹窗还是打印。
_CONSOLE = sys.stdout is not None and sys.stderr is not None
if not _CONSOLE:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import uvicorn
from app.main import app
from app.security import install as install_security
from app import applog, control, meta
from app.instance_lock import InstanceLock

install_security(app)
applog.install(app)
meta.install(app)

BASE_PORT = int(os.environ.get("MMTEST_PORT", "8735"))
NO_BROWSER = os.environ.get("MMTEST_NO_BROWSER", "").strip().lower() in {"true", "yes", "1"}


def _base_dir() -> str:
    """数据目录锚点：打包后必须是 exe 所在目录。

    onefile 模式下 __file__ 指向临时解包目录（每次启动都是新的 _MEIxxxx），
    锁文件若跟着它落盘，第二次双击就会误判"没有实例在跑"，在 8736 再起一个。
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


LOCK_PATH = os.path.join(os.environ.get("MMTEST_WORKSPACE") or
                         os.path.join(_base_dir(), "workspace"),
                         "instance.lock")


def _find_port(start: int) -> int:
    for port in range(start, start + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("没有可用端口")


def _port_busy(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def open_browser(port: int) -> None:
    """等端口真正可连再开浏览器。

    打包后从双击到监听有 5～8s（onefile 解包），原来固定 sleep 1.2s 会在
    服务就绪前打开浏览器，用户看到的是"无法访问此网站"。
    """
    deadline = time.time() + 120
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                break
        time.sleep(0.1)
    if not NO_BROWSER:
        webbrowser.open(f"http://127.0.0.1:{port}")


def _has_console() -> bool:
    """windowed 打包时没有可交互的控制台。"""
    return _CONSOLE


def _say(message: str) -> None:
    """无控制台时 print 会抛 AttributeError（sys.stdout 为 None），统一走这里。"""
    if _has_console():
        try:
            print(message)
        except Exception:
            pass


def _alert(message: str) -> None:
    """没有控制台时用系统弹窗报错，否则双击后只是"什么都没发生"。"""
    if _has_console():
        print(message)
        return
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, "多模态测试平台", 0x10)
    except Exception:
        pass


def _wait_if_console(hint: str = "按回车键关闭本窗口...") -> None:
    """以交互式窗口启动时，等用户确认再退出，避免看似闪退。"""
    if not _has_console():
        return
    try:
        input("\n" + hint)
    except Exception:
        pass


def main() -> int:
    lock = InstanceLock(LOCK_PATH)
    ok, holder = lock.acquire()
    if not ok:
        port = holder.get("port") or BASE_PORT
        applog.info("start.reuse_running_instance", port=port, pid=holder.get("pid"))
        _say(f"平台已在运行：http://127.0.0.1:{port}")
        if not NO_BROWSER:
            webbrowser.open(f"http://127.0.0.1:{port}")
        _wait_if_console("按回车键关闭本窗口（平台仍在后台运行）...")
        return 0

    server = None
    try:
        if _port_busy(BASE_PORT):
            port = _find_port(BASE_PORT + 1)
            _say(f"端口 {BASE_PORT} 被其他程序占用，已改用端口 {port}")
        else:
            port = BASE_PORT
        lock.update(port=port)
        applog.info("start.listen", port=port, version=meta.VERSION,
                    python=meta.info()["python"])
        _say(f"访问地址：http://127.0.0.1:{port}   版本 {meta.VERSION}")
        threading.Thread(target=open_browser, args=(port,), daemon=True).start()
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        server = uvicorn.Server(config)
        # 页面里的「退出程序」走这条路径：置位 should_exit，uvicorn 正常收尾后
        # main() 返回，finally 里释放锁文件。
        control.install(app, shutdown=lambda: setattr(server, "should_exit", True))
        server.run()
        applog.info("stop.requested", port=port)
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception:
        applog.error("start.failed", exc=sys.exc_info()[1])
        # 无控制台模式 sys.stderr 为 None，traceback.print_exc() 自己会抛异常
        if _has_console():
            traceback.print_exc()
        detail = "".join(traceback.format_exception_only(*sys.exc_info()[:2])).strip()
        _alert("启动失败：" + detail + "\n\n详细信息见 workspace/logs/app.log")
        return 1
    finally:
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
