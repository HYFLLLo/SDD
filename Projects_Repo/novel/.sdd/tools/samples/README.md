# T-003 epub 验收样本

由 `make-epub-samples.py` 生成，供 Developer/Tester 独立验收使用。

| 文件 | 用途 |
|------|------|
| `valid-book.epub` | 合法 EPUB 2：mimetype + META-INF/container.xml + OPS/content.opf + OPS/toc.ncx + 3 个中文章节 xhtml（含 `<b>/<em>/<i>` 内联标签，用于验证纯文本化） |
| `corrupt-nocontainer.epub` | 合法 zip 但缺 `META-INF/container.xml` → 应返回 A0704 |
| `corrupt-notzip.epub` | 普通文本伪装 epub（非 zip 结构）→ 应返回 A0704 |

上传命令（Windows Git-Bash，中文用 Python UTF-8 multipart 规避 mojibake，见 experience.md）：
```
POST http://127.0.0.1:8888/api/front/resource/book/upload
form: file=valid-book.epub, bookName, authorName, workDirection=0, categoryId, categoryName, bookDesc
```
