"""图片标注：按解析后的 objects 绘制 bbox（纯 PIL，支持中文路径与中文字体）

坐标系约定：全链路统一使用「EXIF 转正后」的图像坐标——
maas.py 发送给模型前会做 exif_transpose，浏览器展示原图时也自动应用 EXIF，
因此这里读图/量尺寸必须同样转正，否则带 EXIF 旋转的图（手机照片常见）框会整体旋转错位。
"""
import os
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageOps
PALETTE = [
 (231, 76, 60), (46, 134, 222), (39, 174, 96), (241, 165, 31),
 (155, 89, 182), (26, 188, 156), (230, 74, 145), (120, 110, 40)]
_font_cache: Dict[(int, ImageFont.FreeTypeFont)] = {}

def _clip(value, limit=48):
    text = str(value).strip()
    if len(text) <= limit:
        return text
    return text[:limit - 1] + "…"


def _label_value(obj):
    for key in ('label_value', 'labelValue'):
        if obj.get(key) not in (None, ''):
            return str(obj[key])

    attributes = obj.get("attributes") or {}
    if isinstance(attributes, dict) and attributes.get("labelValue") not in (None, ''):
        return str(attributes["labelValue"])
    return ""


def _field_value(obj, key):
    if obj.get(key) not in (None, ''):
        return obj[key]
    attributes = obj.get("attributes") or {}
    if isinstance(attributes, dict):
        if attributes.get(key) not in (None, ''):
            return attributes[key]


def _font(size=20):
    if size in _font_cache:
        return _font_cache[size]
    font = None
    for p in ('C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf', 'C:/Windows/Fonts/simsun.ttc',
              '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc', '/System/Library/Fonts/PingFang.ttc'):
        if os.path.exists(p):
            try:
                font = ImageFont.truetype(p, size)
                break
            except Exception:
                continue

    if font is None:
        font = ImageFont.load_default()
    _font_cache[size] = font
    return font


def get_image_size(image_path):
    with Image.open(image_path) as im:
        im = ImageOps.exif_transpose(im)
        return (
         im.width, im.height)


def draw_objects(image_path, objects, output_path=None, show_fields=None):
    """在图片上绘制 objects 的 bbox 与标签。
    output_path 为 None 时直接返回 PIL Image（试跑等内存场景用）。"""
    if not objects:
        return
    with Image.open(image_path) as im0:
        im = ImageOps.exif_transpose(im0).convert("RGB")
    w, h = im.size
    draw = ImageDraw.Draw(im)
    font = _font(max(16, min(w, h) // 45))
    lw = max(2, min(w, h) // 400)
    for idx, obj in enumerate(objects):
        box = obj.get("bbox")
        if not box:
            norm = obj.get("bbox_normalized")
            if norm:
                box = [
                 norm[0] * w, norm[1] * h, norm[2] * w, norm[3] * h]
        if not box:
            pass
        else:
            x1, y1, x2, y2 = [int(round(v)) for v in box[:4]]
            x1, x2 = sorted((max(0, x1), min(w - 1, x2)))
            y1, y2 = sorted((max(0, y1), min(h - 1, y2)))
            color = PALETTE[idx % len(PALETTE)]
            draw.rectangle([x1, y1, x2, y2], outline=color, width=lw)
            label = str(obj.get("name") or obj.get("labelName") or "目标")
            if obj.get("confidence") is not None:
                try:
                    label += f' {float(obj["confidence"]):.2f}'
                except Exception:
                    pass

            secondary = _clip(_label_value(obj))
            if show_fields:
                extras = [f"{k}:{_clip(_field_value(obj, k), 24)}" for k in show_fields if k not in ('label_value',
                                                                                                     'labelValue') if _field_value(obj, k) is not None]
                if extras:
                    secondary = (secondary + "\n" if secondary else "") + " | ".join(extras)
            text = label + (f"\n{secondary}" if secondary else "")
            tb = draw.multiline_textbbox((0, 0), text, font=font, spacing=3)
            tw, th = tb[2] - tb[0], tb[3] - tb[1]
            pad = 4
            if y1 - th - 2 * pad >= 0:
                by1, by2 = y1 - th - 2 * pad, y1
            else:
                by1, by2 = y2, y2 + th + 2 * pad
            draw.rectangle([x1, by1, x1 + tw + 2 * pad, by2], fill=color)
            draw.multiline_text((x1 + pad, by1 + pad), text, font=font, fill=(255,
                                                                              255,
                                                                              255),
              spacing=3)

    if output_path:
        os.makedirs((os.path.dirname(output_path)), exist_ok=True)
        im.save(output_path, quality=92)
        return output_path
    return im
