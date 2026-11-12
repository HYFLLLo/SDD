# -*- coding: utf-8 -*-
"""
生成 T-003 验收用 epub 测试样本：
  samples/valid-book.epub     —— 合法 EPUB 2（3 个中文章节 + 简介 + 目录）
  samples/corrupt-nocontainer.epub —— 缺 container.xml（A0704 分支）
  samples/corrupt-notzip.epub      —— 伪 zip / 结构损坏（A0704 分支）
输出到 .sdd/tools/samples/  供 Tester 独立验收使用。
"""
import io
import os
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "samples")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------------------
# 合法样本：标准 EPUB 2 结构
# ---------------------------------------------------------------------------
chapters = [
    ("第一章 初入江湖", "<h1>第一章 初入江湖</h1><p>夜色如墨，少年背着一把<b>锈剑</b>独自踏上山路。</p><p>远处传来寒鸦的叫声，他紧了紧衣领。</p>"),
    ("第二章 客栈奇遇", "<h1>第二章 客栈奇遇</h1><p>客栈掌柜是个驼背老人，递来一碗<em>热茶</em>。</p><p>“客官，可是要住店？”老人笑问。</p><p>少年点了点头，手中的锈剑微微发颤。</p>"),
    ("第三章 惊变", "<h1>第三章 惊变</h1><p>子时刚过，客栈灯火俱灭。</p><p>窗外一道黑影闪过，少年翻身而起。<i>来了。</i></p>"),
]

html_template = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh-CN" lang="zh-CN">
<head>
<title>{title}</title>
</head>
<body>{body}</body>
</html>
"""

chapter_files = {}
for i, (title, body) in enumerate(chapters, start=1):
    chapter_files["chapter{}.xhtml".format(i)] = html_template.format(title=title, body=body)

opf = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>测试电子书</dc:title>
    <dc:language>zh-CN</dc:language>
    <dc:creator>测试作者</dc:creator>
    <dc:description>用于 T-003 epub 解析验收的测试图书。</dc:description>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    {items}
  </manifest>
  <spine toc="ncx">
    {spine}
  </spine>
</package>
"""

items = "\n".join(
    '<item id="ch{}" href="chapter{}.xhtml" media-type="application/xhtml+xml"/>'.format(i, i)
    for i in range(1, 4)
)
spine = "\n".join('<itemref idref="ch{}"/>'.format(i) for i in range(1, 4))

navmap = "\n".join(
    '<navPoint id="nav{}" playOrder="{}"><navLabel><text>{}</text></navLabel><content src="chapter{}.xhtml"/></navPoint>'.format(
        i, i, chapters[i - 1][0], i
    )
    for i in range(1, 4)
)
ncx = """<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head><meta name="dtb:uid" content="testbook"/></head>
  <docTitle><text>测试电子书</text></docTitle>
  <navMap>{}</navMap>
</ncx>
""".format(navmap)

container = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

mimetype = "application/epub+zip"

valid_path = os.path.join(OUT, "valid-book.epub")
with zipfile.ZipFile(valid_path, "w", zipfile.ZIP_DEFLATED) as z:
    # EPUB 规范要求 mimetype 必须是第一个条目、stored（无压缩）
    z.writestr(zipfile.ZipInfo("mimetype"), mimetype, zipfile.ZIP_STORED)
    z.writestr("META-INF/container.xml", container)
    z.writestr("OPS/content.opf", opf.format(items=items, spine=spine))
    z.writestr("OPS/toc.ncx", ncx)
    for filename, content in chapter_files.items():
        z.writestr("OPS/" + filename, content)

print("wrote", valid_path, os.path.getsize(valid_path), "bytes")

# ---------------------------------------------------------------------------
# 损坏样本 1：合法 zip 但缺 META-INF/container.xml
# ---------------------------------------------------------------------------
corrupt1 = os.path.join(OUT, "corrupt-nocontainer.epub")
with zipfile.ZipFile(corrupt1, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("OPS/content.opf", opf.format(items=items, spine=spine))
    z.writestr("OPS/chapter1.xhtml", chapter_files["chapter1.xhtml"])
print("wrote", corrupt1, os.path.getsize(corrupt1), "bytes")

# ---------------------------------------------------------------------------
# 损坏样本 2：不是 zip（伪作 epub 内容的普通文件）
# ---------------------------------------------------------------------------
corrupt2 = os.path.join(OUT, "corrupt-notzip.epub")
with io.open(corrupt2, "w", encoding="utf-8") as f:
    f.write("this is not a zip file at all, just plain text pretending to be epub")
print("wrote", corrupt2, os.path.getsize(corrupt2), "bytes")