import os

import pytest


def _png_bytes():
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture()
def spaced_workspace(tmp_path, monkeypatch):
    from app import config

    root = tmp_path / "中文 目录 带空格"
    root.mkdir()
    monkeypatch.setattr(config, "WORKSPACE", str(root))
    monkeypatch.setattr(config, "CONFIG_PATH", str(root / "config.json"))
    yield root


def test_config_roundtrip_in_unicode_spaced_path(spaced_workspace):
    from app import config

    cfg = config.load_config()
    assert os.path.isfile(str(spaced_workspace / "config.json"))
    assert cfg["api"]["sites"]
    cfg["defaults"]["timeout"] = 42
    config.save_config(cfg)
    assert config.load_config()["defaults"]["timeout"] == 42


def test_dataset_crud_in_unicode_spaced_path(spaced_workspace):
    from app import datasets

    project = "项目 甲"
    name = "数据集 一"
    path = datasets.create_dataset(name, project)
    assert os.path.isdir(path)
    assert "项目 甲" in path

    ref = datasets.dataset_ref(project, name)
    dst = datasets.save_upload(ref, "样 图 1.png", _png_bytes(), "子 目录")
    assert os.path.isfile(dst)
    rows = datasets.scan_images(ref)
    assert [r["rel"] for r in rows] == ["子 目录/样 图 1.png"]
    assert datasets.image_path(ref, rows[0]["rel"]) == dst

    datasets.delete_image(ref, rows[0]["rel"])
    assert datasets.scan_images(ref) == []
    datasets.delete_dataset(ref)
    assert not os.path.isdir(path)


def test_legacy_dataset_in_unicode_path(spaced_workspace):
    from app import datasets

    name = "旧 图片 集"
    path = datasets.create_dataset(name)
    assert os.path.isdir(path)
    assert datasets.dataset_ref("未归档项目", name) == "未归档项目::旧 图片 集"
    assert datasets._dataset_dir(name) == datasets._dataset_dir("未归档项目::旧 图片 集")


def test_rejects_traversal_in_unicode_names(spaced_workspace):
    from app import datasets

    for bad in ("../逃逸", "..\\逃逸", "a::b", "x/y", 'q"z'):
        with pytest.raises(ValueError):
            datasets.create_dataset(bad, "项目 甲")


def test_safe_path_blocks_escape_from_unicode_base(spaced_workspace):
    from app import config

    base = str(spaced_workspace)
    assert config.safe_path(base, "子 目录", "x.png").startswith(base)
    with pytest.raises(ValueError):
        config.safe_path(base, "..", "外 部")


def test_long_nested_dataset_path(spaced_workspace):
    from app import datasets

    segment = "子目录-" + "x" * 30
    sub = "/".join(segment for _ in range(8))
    ref = datasets.dataset_ref("项目 甲", "数据集 一")
    datasets.create_dataset("数据集 一", "项目 甲")
    dst = datasets.save_upload(ref, "长 路径.png", _png_bytes(), sub)
    assert os.path.isfile(dst)
    rows = datasets.scan_images(ref)
    assert rows[0]["rel"].startswith(segment)
    assert len(dst) > 260
