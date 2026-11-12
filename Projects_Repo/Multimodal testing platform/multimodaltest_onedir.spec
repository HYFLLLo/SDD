# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 单文件构建：pyinstaller multimodaltest.spec
# 资源路径与 app/main.py、app/demo.py、app/main.api_help 中的 _MEIPASS 约定一致。

import json
import os
import subprocess
import time

from PyInstaller.utils.hooks import collect_submodules


def _git(*args, **kwargs):
    default = kwargs.get("default", "")
    try:
        return subprocess.check_output(
            ["git"] + list(args), stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return default


def write_build_info():
    """构建时写入版本/提交信息，供 /api/version 读取（打包进 _MEIPASS）。"""
    info = {
        "build_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "git_commit": _git("rev-parse", "--short", "HEAD")[:12],
        "git_dirty": bool(_git("status", "--porcelain")),
    }
    os.makedirs("build", exist_ok=True)
    with open(os.path.join("build", "build_info.json"), "w", encoding="utf-8") as fh:
        json.dump(info, fh, ensure_ascii=False, indent=2)
    return info


build_info = write_build_info()

hiddenimports = (
    collect_submodules("uvicorn")
    + [
        "app.annotate", "app.comparison", "app.config", "app.datasets", "app.demo",
        "app.applog", "app.dircache", "app.evaluate", "app.extractor",
        "app.instance_lock", "app.judge", "app.maas", "app.meta",
        "app.prompt_ai", "app.prompt_profiles", "app.prompts", "app.reviews",
        "app.runner", "app.schema", "app.security", "app.stats", "app.trial",
        "app.truth", "app.workflow",
    ]
)

# 运行时不使用、但会被 openai 2.x 的可选分支静态扫描进来的重型包。
EXCLUDES = [
    "pytest", "tkinter",
    "numpy", "boto3", "botocore", "s3transfer", "jmespath",
    "cryptography",
    "tzdata",
    "PIL.AvifImagePlugin",
    "litellm", "litellm_enterprise", "litellm_proxy_extras",
    "matplotlib", "pandas", "scipy", "sympy", "torch", "transformers",
    "IPython", "win32com", "pythoncom", "pywintypes",
]

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("web", "web"),
        ("demo_pack", "demo_pack"),
        ("操作指南.txt", "."),
        ("build/build_info.json", "."),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
)

# zoneinfo 的 hook 会无条件收集 tzdata 的 605 个时区文件；本应用不做时区换算。
a.datas = [d for d in a.datas
           if not d[0].replace(chr(92), "/").startswith("tzdata/")]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="多模态测试平台",
    exclude_binaries=True,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # 无控制台：黑窗口就是服务进程本体，点叉等于杀进程。
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="MTO-app",
)
