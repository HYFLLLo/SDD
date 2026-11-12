package io.github.xxyopen.novel.core.common.util;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.zip.CRC32;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;
import org.junit.jupiter.api.Test;

/**
 * EpubBookParser 单元测试。
 * <p>
 * 仅依赖 JDK zip + jsoup，不启动 Spring 上下文。验证：
 * 正常 epub 按 spine 顺序解析正文为纯文本、损坏 epub / 缺 container.xml / 空文件均返回空列表。
 */
class EpubBookParserTest {

    private static final String CONTAINER_XML =
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            + "<container version=\"1.0\" xmlns=\"urn:oasis:names:tc:opendocument:xmlns:container\">\n"
            + "  <rootfiles>\n"
            + "    <rootfile full-path=\"OEBPS/content.opf\" media-type=\"application/oebps-package+xml\"/>\n"
            + "  </rootfiles>\n"
            + "</container>";

    private static final String OPF_XML =
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            + "<package xmlns=\"http://www.idpf.org/2007/opf\" version=\"3.0\" unique-identifier=\"uid\">\n"
            + "  <metadata xmlns:dc=\"http://purl.org/dc/elements/1.1/\">\n"
            + "    <dc:title>测试书名</dc:title>\n"
            + "  </metadata>\n"
            + "  <manifest>\n"
            + "    <item id=\"c3\" href=\"text/chapter3.xhtml\" media-type=\"application/xhtml+xml\"/>\n"
            + "    <item id=\"c1\" href=\"text/chapter1.xhtml\" media-type=\"application/xhtml+xml\"/>\n"
            + "    <item id=\"c2\" href=\"text/chapter2.xhtml\" media-type=\"application/xhtml+xml\"/>\n"
            + "  </manifest>\n"
            + "  <spine toc=\"ncx\">\n"
            + "    <itemref idref=\"c1\"/>\n"
            + "    <itemref idref=\"c2\"/>\n"
            + "    <itemref idref=\"c3\"/>\n"
            + "  </spine>\n"
            + "</package>";

    private static final String CHAPTER_XHTML_TEMPLATE =
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            + "<!DOCTYPE html>\n"
            + "<html xmlns=\"http://www.w3.org/1999/xhtml\">\n"
            + "  <head><title>%（TITLE）</title><style>.x{color:red}</style></head>\n"
            + "  <body>\n"
            + "    <h1>%（TITLE）</h1>\n"
            + "    <p>第%（IDX）段正文，包含<i>斜体</i>与<b>加粗</b>样式。</p>\n"
            + "    <p>第二段：script 脚本不应出现<script type=\"text/javascript\">alert('x');</script>。</p>\n"
            + "  </body>\n"
            + "</html>";

    private static byte[] buildEpub() throws IOException {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(bos, StandardCharsets.UTF_8)) {
            putEntry(zos, "META-INF/container.xml", CONTAINER_XML);
            putEntry(zos, "OEBPS/content.opf", OPF_XML);
            putEntry(zos, "OEBPS/text/chapter1.xhtml",
                CHAPTER_XHTML_TEMPLATE.replace("%（IDX）", "一").replace("%（TITLE）", "第一章 初入江湖"));
            putEntry(zos, "OEBPS/text/chapter2.xhtml",
                CHAPTER_XHTML_TEMPLATE.replace("%（IDX）", "二").replace("%（TITLE）", "第二章 风起云涌"));
            putEntry(zos, "OEBPS/text/chapter3.xhtml",
                CHAPTER_XHTML_TEMPLATE.replace("%（IDX）", "三").replace("%（TITLE）", "第三章 决战紫禁"));
        }
        return bos.toByteArray();
    }

    private static void putEntry(ZipOutputStream zos, String path, String content)
        throws IOException {
        byte[] bytes = content.getBytes(StandardCharsets.UTF_8);
        ZipEntry entry = new ZipEntry(path);
        CRC32 crc = new CRC32();
        crc.update(bytes);
        entry.setCrc(crc.getValue());
        zos.putNextEntry(entry);
        zos.write(bytes);
        zos.closeEntry();
    }

    @Test
    void parseEpubParsesSpineOrderAndCleanText() throws IOException {
        List<TxtBookParser.Chapter> chapters = EpubBookParser.parseEpub(buildEpub());
        assertEquals(3, chapters.size());
        // spine 顺序：c1 → c2 → c3（manifest 声明顺序与 spine 不同，验证以 spine 为准）
        assertEquals("第一章 初入江湖", chapters.get(0).getChapterName());
        assertEquals("第二章 风起云涌", chapters.get(1).getChapterName());
        assertEquals("第三章 决战紫禁", chapters.get(2).getChapterName());
        // 正文为纯文本：无 HTML 标签 / 样式 / script 残留
        String content = chapters.get(0).getContent();
        assertTrue(content.contains("第一段正文，包含斜体与加粗样式。"));
        assertTrue(content.contains("第二段：script 脚本不应出现。"));
        assertTrue(!content.contains("<p>") && !content.contains("<i>") && !content.contains("<style>"));
        assertTrue(!content.contains("alert") && !content.contains("color:red"));
    }

    @Test
    void parseEpubFallsBackChapterNameWhenNoTitle() throws IOException {
        String xhtml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            + "<html xmlns=\"http://www.w3.org/1999/xhtml\"><head></head><body>只有正文</body></html>";
        byte[] bytes = buildEpubWithSingleChapter(xhtml);
        List<TxtBookParser.Chapter> chapters = EpubBookParser.parseEpub(bytes);
        assertEquals(1, chapters.size());
        assertEquals("第1章", chapters.get(0).getChapterName());
        assertTrue(chapters.get(0).getContent().contains("只有正文"));
    }

    @Test
    void parseEpubReturnsEmptyOnMissingContainer() throws IOException {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(bos)) {
            putEntry(zos, "OEBPS/content.opf", OPF_XML);
        }
        assertTrue(EpubBookParser.parseEpub(bos.toByteArray()).isEmpty());
    }

    @Test
    void parseEpubReturnsEmptyOnBrokenZip() {
        // 伪造 .epub 后缀但内容不是 zip → ZipFile 构造失败 → 空列表
        assertTrue(EpubBookParser.parseEpub("this is not a zip".getBytes(StandardCharsets.UTF_8))
            .isEmpty());
    }

    @Test
    void parseEpubReturnsEmptyOnEmptyBytes() {
        assertTrue(EpubBookParser.parseEpub(new byte[0]).isEmpty());
        assertTrue(EpubBookParser.parseEpub(null).isEmpty());
    }

    @Test
    void parseEpubReturnsEmptyWhenSpineRefMissingInManifest() throws IOException {
        String opf = OPF_XML.replace(
            "<itemref idref=\"c1\"/>\n    <itemref idref=\"c2\"/>",
            "<itemref idref=\"c1\"/>\n    <itemref idref=\"missing\"/>");
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(bos)) {
            putEntry(zos, "META-INF/container.xml", CONTAINER_XML);
            putEntry(zos, "OEBPS/content.opf", opf);
            putEntry(zos, "OEBPS/text/chapter1.xhtml",
                CHAPTER_XHTML_TEMPLATE.replace("%（IDX）", "一").replace("%（TITLE）", "第一章"));
        }
        assertTrue(EpubBookParser.parseEpub(bos.toByteArray()).isEmpty());
    }

    @Test
    void parseEpubDecodesPercentEncodedHref() throws IOException {
        // 真实 epub 的 href 常为 IRI 百分比编码（如 "text/第 1 章.xhtml" → text/%E7%AC%AC%201%20%E7%AB%A0.xhtml）
        String opf = OPF_XML
            .replace("href=\"text/chapter1.xhtml\"",
                "href=\"text/%E7%AC%AC%201%20%E7%AB%A0.xhtml\"")
            .replace(
                "    <item id=\"c1\" href=\"text/chapter1.xhtml\" media-type=\"application/xhtml+xml\"/>\n"
                    + "    <item id=\"c2\" href=\"text/chapter2.xhtml\" media-type=\"application/xhtml+xml\"/>\n"
                    + "    <item id=\"c3\" href=\"text/chapter3.xhtml\" media-type=\"application/xhtml+xml\"/>",
                "    <item id=\"c1\" href=\"text/chapter1.xhtml\" media-type=\"application/xhtml+xml\"/>")
            .replace(
                "    <itemref idref=\"c1\"/>\n    <itemref idref=\"c2\"/>\n    <itemref idref=\"c3\"/>",
                "    <itemref idref=\"c1\"/>");
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(bos)) {
            putEntry(zos, "META-INF/container.xml", CONTAINER_XML);
            putEntry(zos, "OEBPS/content.opf", opf);
            // 条目名含空格与中文（URLDecoder 的 +  不应被当作空格）
            putEntry(zos, "OEBPS/text/第 1 章.xhtml",
                CHAPTER_XHTML_TEMPLATE.replace("%（IDX）", "一").replace("%（TITLE）", "标题"));
        }
        List<TxtBookParser.Chapter> chapters = EpubBookParser.parseEpub(bos.toByteArray());
        assertEquals(1, chapters.size());
        assertEquals("标题", chapters.get(0).getChapterName());
    }

    @Test
    void parseEpubHandlesPrefixedNamespaceOpf() throws IOException {
        // 兼容带命名空间前缀的 OPF（如 opf:item / opf:itemref）
        String prefixedOpf = OPF_XML
            .replace("<package xmlns=\"http://www.idpf.org/2007/opf\"",
                "<package xmlns:opf=\"http://www.idpf.org/2007/opf\"")
            .replace("<manifest>", "<opf:manifest>")
            .replace("</manifest>", "</opf:manifest>")
            .replace("<item ", "<opf:item ")
            .replace("</item>", "</opf:item>")
            .replace("<spine", "<opf:spine")
            .replace("</spine>", "</opf:spine>")
            .replace("<itemref ", "<opf:itemref ")
            .replace("/>", " />");
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(bos)) {
            putEntry(zos, "META-INF/container.xml", CONTAINER_XML);
            putEntry(zos, "OEBPS/content.opf", prefixedOpf);
            putEntry(zos, "OEBPS/text/chapter1.xhtml",
                CHAPTER_XHTML_TEMPLATE.replace("%（IDX）", "一").replace("%（TITLE）", "前缀命名空间"));
            putEntry(zos, "OEBPS/text/chapter2.xhtml",
                CHAPTER_XHTML_TEMPLATE.replace("%（IDX）", "二").replace("%（TITLE）", "第二章"));
            putEntry(zos, "OEBPS/text/chapter3.xhtml",
                CHAPTER_XHTML_TEMPLATE.replace("%（IDX）", "三").replace("%（TITLE）", "第三章"));
        }
        List<TxtBookParser.Chapter> chapters = EpubBookParser.parseEpub(bos.toByteArray());
        assertEquals(3, chapters.size());
        assertEquals("前缀命名空间", chapters.get(0).getChapterName());
        assertEquals("第二章", chapters.get(1).getChapterName());
    }

    private static byte[] buildEpubWithSingleChapter(String xhtml)
        throws IOException {
        String opfSingle = OPF_XML
            .replace(
                "    <item id=\"c1\" href=\"text/chapter1.xhtml\" media-type=\"application/xhtml+xml\"/>\n"
                    + "    <item id=\"c2\" href=\"text/chapter2.xhtml\" media-type=\"application/xhtml+xml\"/>\n"
                    + "    <item id=\"c3\" href=\"text/chapter3.xhtml\" media-type=\"application/xhtml+xml\"/>",
                "    <item id=\"c1\" href=\"text/chapter1.xhtml\" media-type=\"application/xhtml+xml\"/>")
            .replace(
                "    <itemref idref=\"c1\"/>\n    <itemref idref=\"c2\"/>\n    <itemref idref=\"c3\"/>",
                "    <itemref idref=\"c1\"/>");
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(bos)) {
            putEntry(zos, "META-INF/container.xml", CONTAINER_XML);
            putEntry(zos, "OEBPS/content.opf", opfSingle);
            putEntry(zos, "OEBPS/text/chapter1.xhtml", xhtml);
        }
        return bos.toByteArray();
    }
}