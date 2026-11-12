def _reencode_jpeg(image_path):
    """按原始分辨率重编码为 JPEG；逐步降质量直到低于阈值。失败返回 None。"""
    try:
        from PIL import Image, ImageOps
    except Exception:
        return

    try:
        with Image.open(image_path) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
                background = Image.new("RGB", im.size, (255, 255, 255))
                rgba = im.convert("RGBA")
                background.paste(rgba, mask=rgba.split()[-1])
                im = background
            elif im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            best = None
            for quality in (_IMAGE_JPEG_QUALITY, 75, 65, 55):
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=quality, optimize=True)
                data = buf.getvalue()
                if not data:
                    continue
                if best is None or len(data) < len(best):
                    best = data
                if len(data) <= _IMAGE_REENCODE_THRESHOLD:
                    break
        return best
    except Exception:
        return


