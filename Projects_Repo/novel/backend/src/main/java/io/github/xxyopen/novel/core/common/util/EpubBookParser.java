package io.github.xxyopen.novel.core.common.util;

import io.github.xxyopen.novel.core.constant.SystemConfigConsts;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.parser.Parser;

/**
 * epub 电子书解析工具。
 * <p>
 * epub 本质是一个 zip 容器，采用 JDK 内置 {@link ZipFile} 读取，无需第三方解压库；
 * 正文提取使用 jsoup 将每个 spine 条目（xhtml）解析为纯文本。
 * 解析链路：META-INF/container.xml → OPF（manifest + spine）→ 按 spine idref 顺序逐个读取 xhtml。
 * 任一步骤结构不完整（zip 损坏 / 缺 container.xml / OPF 结构不完整 / 无有效章节）均视为解析失败，
 * 由调用方统一映射错误码（如 A0704），不产生脏数据。
 */
public final class EpubBookParser {

    private EpubBookParser() {
        throw new IllegalStateException(SystemConfigConsts.CONST_INSTANCE_EXCEPTION_MSG);
    }

    /** EPUB 容器描述文件（固定路径） */
    private static final String CONTAINER_FILE = "META-INF/container.xml";

    /** 段落分隔占位符：jsoup text() 会折叠空白，先标记块级元素边界再还原为换行 */
    private static final char LINE_BREAK_MARKER = '\u0001';

    /** 不换行空格（U+00A0） */
    private static final char NBSP = '\u00A0';

    /** jsoup text() 会折叠空白，标记块级元素边界的块元素选择器 */
    private static final String BLOCK_SELECTOR =
        "br, p, div, h1, h2, h3, h4, h5, h6, li, blockquote, section, article, tr";

    /**
     * 解析 epub 文件字节内容，按 OPF spine 顺序返回章节列表。
     *
     * @param fileBytes epub 文件完整字节内容
     * @return 章节列表（chapterName + content），正文为清洗后的纯文本；解析失败返回空列表
     */
    public static List<TxtBookParser.Chapter> parseEpub(byte[] fileBytes) {
        if (fileBytes == null || fileBytes.length == 0) {
            return new ArrayList<>();
        }
        File temp = null;
        try {
            temp = toTempFile(fileBytes);
            try (ZipFile zipFile = new ZipFile(temp)) {
                // 1. container.xml → rootfile（OPF 路径）
                String opfPath = readContainerOpfPath(zipFile);
                if (opfPath == null) {
                    return new ArrayList<>();
                }
                // 2. 读取 OPF 的 manifest 与 spine
                byte[] opfBytes = readEntry(zipFile, opfPath);
                if (opfBytes == null || opfBytes.length == 0) {
                    return new ArrayList<>();
                }
                OpfInfo opfInfo = parseOpf(decodeXml(opfBytes));
                if (opfInfo.getManifestItems().isEmpty() || opfInfo.getSpineIdrefs().isEmpty()) {
                    return new ArrayList<>();
                }
                // 3. 按 spine 顺序逐个读取 xhtml，提取章节标题与正文纯文本
                List<TxtBookParser.Chapter> chapters = new ArrayList<>();
                for (String idref : opfInfo.getSpineIdrefs()) {
                    String href = opfInfo.getManifestItems().get(idref);
                    if (href == null) {
                        // spine 引用了 manifest 中不存在的条目 → 解析失败
                        return new ArrayList<>();
                    }
                    byte[] xhtmlBytes = readEntry(zipFile, resolvePath(opfPath, href));
                    if (xhtmlBytes == null) {
                        // spine 条目文件不存在 → 解析失败
                        return new ArrayList<>();
                    }
                    TxtBookParser.Chapter chapter = parseChapter(xhtmlBytes, chapters.size());
                    if (chapter != null) {
                        chapters.add(chapter);
                    }
                }
                return chapters;
            }
        } catch (IOException | RuntimeException e) {
            // zip 结构损坏 / 临时文件写入失败 / 条目无法读取等 → 视为解析失败
            return new ArrayList<>();
        } finally {
            if (temp != null) {
                temp.delete();
            }
        }
    }

    /**
     * 将字节数组落盘为临时 zip 文件，供 {@link ZipFile} 按名随机访问
     * （container → OPF → spine xhtml 的解析链路需要多次按名读取）。
     *
     * @param fileBytes 文件字节
     * @return 临时文件（调用方在 finally 中删除）
     * @throws IOException 临时文件写入失败
     */
    private static File toTempFile(byte[] fileBytes) throws IOException {
        File temp = File.createTempFile("epub-upload-", ".zip");
        try {
            try (FileOutputStream fos = new FileOutputStream(temp)) {
                fos.write(fileBytes);
            }
        } catch (IOException e) {
            temp.delete();
            throw e;
        }
        return temp;
    }

    /**
     * 读取 container.xml 中 rootfile 的 full-path（OPF 相对路径）。
     *
     * @param zipFile 打开的 zip
     * @return OPF 路径；结构不完整返回 null
     */
    private static String readContainerOpfPath(ZipFile zipFile) throws IOException {
        byte[] containerBytes = readEntry(zipFile, CONTAINER_FILE);
        if (containerBytes == null || containerBytes.length == 0) {
            return null;
        }
        Document doc = Jsoup.parse(decodeXml(containerBytes), "", Parser.xmlParser());
        for (Element el : doc.getAllElements()) {
            if (!"rootfile".equals(localName(el.tagName()))) {
                continue;
            }
            String fullPath = el.attr("full-path");
            if (!fullPath.trim().isEmpty()) {
                return fullPath.trim();
            }
        }
        return null;
    }

    /**
     * 解析 OPF 文件：提取 manifest（item id → href）与 spine（idref 顺序即阅读顺序）。
     * 按标签本地名匹配，兼容默认命名空间与带前缀命名空间两种写法。
     *
     * @param opfXml OPF 文件内容
     * @return manifest 与 spine 解析结果；结构不完整返回空结构
     */
    private static OpfInfo parseOpf(String opfXml) {
        Map<String, String> manifestItems = new HashMap<>();
        List<String> spineIdrefs = new ArrayList<>();
        try {
            Document doc = Jsoup.parse(opfXml, "", Parser.xmlParser());
            for (Element el : doc.getAllElements()) {
                String local = localName(el.tagName());
                if ("item".equals(local)) {
                    String id = el.attr("id");
                    String href = el.attr("href");
                    if (!id.isEmpty() && !href.isEmpty()) {
                        manifestItems.put(id, href);
                    }
                } else if ("itemref".equals(local)) {
                    String idref = el.attr("idref");
                    if (!idref.isEmpty()) {
                        spineIdrefs.add(idref);
                    }
                }
            }
        } catch (RuntimeException e) {
            // 解析失败 → 空结构（由调用方判定解析失败）
        }
        return OpfInfo.builder().manifestItems(manifestItems).spineIdrefs(spineIdrefs).build();
    }

    /**
     * 去除标签名上的命名空间前缀（如 opf:item → item）。
     */
    private static String localName(String tagName) {
        int colon = tagName.indexOf(':');
        return colon >= 0 ? tagName.substring(colon + 1) : tagName;
    }

    /**
     * 解析单个 xhtml 文件为章节：优先 {@code <title>} 取章节名，其次首个 {@code <h1>~<h3>}，
     * 都没有则用「第N章」兜底；正文去 head/script/style 后取 body 文本，保留段落换行并清洗为纯文本。
     *
     * @param xhtmlBytes xhtml 文件字节
     * @param index      章节序号（从 0 开始，用于「第N章」兜底）
     * @return 章节；正文提取为空返回 null
     */
    private static TxtBookParser.Chapter parseChapter(byte[] xhtmlBytes, int index) {
        final Document doc;
        try {
            // 交给 jsoup 做编码探测（BOM / meta charset）
            doc = Jsoup.parse(new ByteArrayInputStream(xhtmlBytes), null, "");
        } catch (IOException | RuntimeException e) {
            return null;
        }
        String chapterName = extractTitle(doc);
        if (chapterName == null) {
            chapterName = "第" + (index + 1) + "章";
        }
        String content = extractContent(doc);
        if (content == null) {
            return null;
        }
        return TxtBookParser.Chapter.builder()
            .chapterName(chapterName)
            .content(content)
            .build();
    }

    /**
     * 从已解析的 xhtml 文档中提取正文纯文本。
     *
     * @param doc 已解析的 Document
     * @return 清洗后的纯文本（块级元素之间以换行分隔）；无正文返回 null
     */
    private static String extractContent(Document doc) {
        // 去除 head（含 title）、脚本与样式等布局/噪声标签
        doc.select("script, style, link, meta, head").remove();
        Element body = doc.body();
        if (body == null) {
            return null;
        }
        // 在块级元素/br 之后标记段落边界，text() 折叠空白后再还原为换行
        for (Element block : body.select(BLOCK_SELECTOR)) {
            block.appendText(String.valueOf(LINE_BREAK_MARKER));
        }
        String text = body.text();
        text = text.replace(LINE_BREAK_MARKER, '\n');
        text = text.replace(NBSP, ' ');
        String cleaned = TxtBookParser.cleanText(text);
        return cleaned.isEmpty() ? null : cleaned;
    }

    /**
     * 从已解析的 xhtml 文档中提取章节名：优先 {@code <title>}，其次首个 {@code <h1>~<h3>}。
     *
     * @param doc 已解析的 Document
     * @return 章节名；提取不到返回 null
     */
    private static String extractTitle(Document doc) {
        Element title = doc.selectFirst("title");
        if (title != null) {
            String t = TxtBookParser.cleanText(title.text());
            if (t != null && !t.isEmpty()) {
                return t;
            }
        }
        Element heading = doc.selectFirst("h1, h2, h3");
        if (heading != null) {
            String h = TxtBookParser.cleanText(heading.text());
            if (h != null && !h.isEmpty()) {
                return h;
            }
        }
        return null;
    }

    /**
     * 解码 XML 文本：剥离 UTF-8 / UTF-16 BOM 后按对应编码解码（EPUB 规范要求 UTF-8 或 UTF-16）。
     *
     * @param bytes XML 文件字节
     * @return 解码后的字符串
     */
    private static String decodeXml(byte[] bytes) {
        if (bytes.length >= 3
            && (bytes[0] & 0xFF) == 0xEF && (bytes[1] & 0xFF) == 0xBB && (bytes[2] & 0xFF) == 0xBF) {
            // UTF-8 BOM
            return new String(bytes, 3, bytes.length - 3, StandardCharsets.UTF_8);
        }
        if (bytes.length >= 2 && (bytes[0] & 0xFF) == 0xFF && (bytes[1] & 0xFF) == 0xFE) {
            // UTF-16 LE BOM
            return new String(bytes, 2, bytes.length - 2, StandardCharsets.UTF_16LE);
        }
        if (bytes.length >= 2 && (bytes[0] & 0xFF) == 0xFE && (bytes[1] & 0xFF) == 0xFF) {
            // UTF-16 BE BOM
            return new String(bytes, 2, bytes.length - 2, StandardCharsets.UTF_16BE);
        }
        return new String(bytes, StandardCharsets.UTF_8);
    }

    /**
     * 读取 zip 中指定条目的完整字节内容。
     *
     * @return 条目字节；条目不存在或为目录返回 null
     */
    private static byte[] readEntry(ZipFile zipFile, String entryPath) throws IOException {
        if (entryPath == null || entryPath.isEmpty()) {
            return null;
        }
        ZipEntry entry = zipFile.getEntry(entryPath);
        if (entry == null || entry.isDirectory()) {
            return null;
        }
        try (InputStream in = zipFile.getInputStream(entry);
            ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int len;
            while ((len = in.read(buffer)) != -1) {
                out.write(buffer, 0, len);
            }
            return out.toByteArray();
        }
    }

    /**
     * 将 OPF 的 href 解析为相对 zip 根目录的条目路径。
     * 处理：去掉 fragment/query、百分比解码（EPUB 规范 href 为 IRI）、相对路径拼接。
     *
     * @param opfPath OPF 在 zip 中的路径
     * @param href    manifest 中 item 的 href
     * @return zip 条目路径；解析失败返回原 href
     */
    private static String resolvePath(String opfPath, String href) {
        if (href == null || href.isEmpty()) {
            return href;
        }
        // 去掉 fragment/query
        int hash = href.indexOf('#');
        if (hash >= 0) {
            href = href.substring(0, hash);
        }
        int query = href.indexOf('?');
        if (query >= 0) {
            href = href.substring(0, query);
        }
        // 百分比解码（EPUB 规范 href 为 IRI）：先把 %XX 还原为字节，再整体按 UTF-8 解码，
        // 避免把多字节 UTF-8 逐字节转成 Latin-1 字符；+ 保持字面加号（不是空格）
        try {
            href = percentDecode(href);
        } catch (RuntimeException e) {
            // 无法解码时按原文处理
        }
        if (href.startsWith("/")) {
            return href.substring(1);
        }
        int lastSlash = opfPath.lastIndexOf('/');
        String baseDir = lastSlash >= 0 ? opfPath.substring(0, lastSlash) : "";
        return baseDir.isEmpty() ? href : baseDir + "/" + href;
    }

    /**
     * 按 URI 规范百分比解码：把所有 %XX 还原为字节序列，再整体按 UTF-8 解码。
     * 与 {@link java.net.URLDecoder} 的区别：保留字面加号 +，不将其当作空格。
     *
     * @param s 待解码字符串
     * @return 解码后的字符串
     */
    private static String percentDecode(String s) {
        if (s.indexOf('%') < 0) {
            return s;
        }
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '%' && i + 2 < s.length()) {
                int high = Character.digit(s.charAt(i + 1), 16);
                int low = Character.digit(s.charAt(i + 2), 16);
                if (high >= 0 && low >= 0) {
                    bytes.write((high << 4) | low);
                    i += 2;
                    continue;
                }
            }
            // 非 %XX：把该字符以 UTF-8 编码写入字节流，保证与字面内容混用时一致
            byte[] charBytes = String.valueOf(c).getBytes(StandardCharsets.UTF_8);
            bytes.write(charBytes, 0, charBytes.length);
        }
        return new String(bytes.toByteArray(), StandardCharsets.UTF_8);
    }

    @lombok.Getter
    @lombok.Builder
    public static class OpfInfo {

        /** manifest：item id → href */
        private final Map<String, String> manifestItems;

        /** spine：idref 顺序即阅读顺序 */
        private final List<String> spineIdrefs;
    }
}