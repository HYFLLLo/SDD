import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# app.config reads MMTEST_WORKSPACE at import time; set it before importing app.
_WS = tempfile.mkdtemp(prefix="mmtest-pytest-")
os.environ["MMTEST_WORKSPACE"] = _WS
os.environ.setdefault("MMTEST_NO_BROWSER", "1")


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch):
    import app.config as config

    monkeypatch.setattr(config, "WORKSPACE", str(tmp_path))
    monkeypatch.setattr(config, "CONFIG_PATH", str(tmp_path / "config.json"))
    return tmp_path