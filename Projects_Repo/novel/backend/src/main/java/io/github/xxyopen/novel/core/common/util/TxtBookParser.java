package io.github.xxyopen.novel.core.common.util;

import io.github.xxyopen.novel.core.constant.SystemConfigConsts;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.Charset;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;
import lombok.Builder;
import lombok.Getter;

/**
 * txt 电子书解析工具。
 * <p>
 * 负责：BOM/编码识别（UTF-8 BOM / UTF-8 / GBK）、章节切分（中文与英文章节标题正则）、
 * 正文清洗（去除连续空行、首尾空白、html 标签）。仅使用 JDK 内置能力，不引入第三方依赖。
 */
public final class TxtBookParser {

    private TxtBookParser() {
        throw new IllegalStateException(SystemConfigConsts.CONST_INSTANCE_EXCEPTION_MSG);
    }

    /** 乱码占比阈值：超过该比例视为二进制/乱码文件 */
    private static final double GIBBERISH_RATIO_THRESHOLD = 0.1;

    /**
     * 章节标题匹配模式（每行匹配，可含空格/书名号）。
     * <p>
     * 兼容：第一章 / 第12回 / 第 001 章 / 第一卷 / 序章 / 楔子 / 引子 / 前言 / 后记 / 番外 /
     * Chapter 1 / CHAPTER One。
     */
    private static final Pattern CHAPTER_PATTERN = Pattern.compile(
        "^(?:第\\s*[0-9０-９一二三四五六七八九十百千万零两]+\\s*[章节回卷部篇集]"
            + "|序章|楔子|引子|前言|后记|番外"
            + "|[Cc][Hh][Aa][Pp][Tt][Ee][Rr]\\s*[0-9０-９一二三四五六七八九十百千万零两]+"
            + "|[Cc][Hh][Aa][Pp]\\s*[0-9]+)"
            + "\\s*[《\"“]?.*$");

    /**
     * 解析 txt 文件字节内容，返回拆分后的章节列表。
     *
     * @param fileBytes 文件完整字节内容（可能带 BOM）
     * @return 章节列表（chapterName + content），正文为清洗后的纯文本
     */
    public static List<Chapter> parseTxt(byte[] fileBytes) {
        // 1. 编码识别
        String text = readText(fileBytes);
        if (text == null || text.isEmpty()) {
            return new ArrayList<>();
        }
        // 2. 清洗 html 标签与连续空行
        text = cleanText(text);
        // 3. 章节切分
        return splitChapters(text);
    }

    /**
     * 识别文本编码并解码为字符串。
     * <p>
     * 探测顺序：UTF-8 BOM → 合法 UTF-8 → GBK。UTF-8 严格解码遇非法字节时回退 GBK。
     */
    public static String readText(byte[] bytes) {
        if (bytes == null || bytes.length == 0) {
            return "";
        }
        // UTF-8 BOM 探测
        if (bytes.length >= 3
            && (bytes[0] & 0xFF) == 0xEF
            && (bytes[1] & 0xFF) == 0xBB
            && (bytes[2] & 0xFF) == 0xBF) {
            return new String(bytes, 3, bytes.length - 3, StandardCharsets.UTF_8);
        }
        // 合法 UTF-8 则按 UTF-8 解码
        String utf8 = tryDecode(bytes, StandardCharsets.UTF_8);
        if (utf8 != null) {
            return utf8;
        }
        // 回退 GBK
        return new String(bytes, Charset.forName("GBK"));
    }

    private static String tryDecode(byte[] bytes, Charset charset) {
        try {
            charset.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT)
                .decode(ByteBuffer.wrap(bytes));
            return new String(bytes, charset);
        } catch (CharacterCodingException e) {
            return null;
        }
    }

    /**
     * 判断解码后的文本是否为乱码（二进制内容伪装成 txt）。
     * <p>
     * 统计替换字符（U+FFFD）与异常控制字符占比，超过阈值视为乱码。
     */
    public static boolean isGibberish(String text) {
        if (text == null || text.isEmpty()) {
            return false;
        }
        int bad = 0;
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            if (c == '�') {
                bad++;
            } else if (Character.isISOControl(c)
                && c != '\n' && c != '\r' && c != '\t') {
                bad++;
            }
        }
        return (double) bad / text.length() > GIBBERISH_RATIO_THRESHOLD;
    }

    /**
     * 清洗正文：去除 html 标签、去除每行首尾空白、合并连续空行为单行。
     */
    public static String cleanText(String text) {
        if (text == null || text.isEmpty()) {
            return text;
        }
        // 去除 html 标签
        text = text.replaceAll("(?is)<[^>]+>", "");
        String[] lines = text.split("\\r?\\n");
        StringBuilder sb = new StringBuilder();
        boolean lastBlank = false;
        for (String line : lines) {
            String trimmed = line.trim();
            if (trimmed.isEmpty()) {
                if (!lastBlank) {
                    sb.append('\n');
                }
                lastBlank = true;
            } else {
                sb.append(trimmed).append('\n');
                lastBlank = false;
            }
        }
        return sb.toString().trim();
    }

    /**
     * 章节切分：按章节标题正则切分，正文放在相邻标题之间。
     * 若无任何章节标题匹配，则整篇作为单章（章节名为「正文」）；首章标题之前的
     * 零散内容（书名页/版权页等）并入第一章。
     *
     * @return 章节列表；正文为空（仅标题行）的章节会被丢弃
     */
    public static List<Chapter> splitChapters(String text) {
        List<Chapter> result = new ArrayList<>();
        if (text == null || text.isEmpty()) {
            return result;
        }
        String[] lines = text.split("\\r?\\n");
        List<String> titles = new ArrayList<>();
        List<StringBuilder> contents = new ArrayList<>();
        StringBuilder leading = new StringBuilder();
        for (String line : lines) {
            String trimmed = line.trim();
            if (!trimmed.isEmpty() && CHAPTER_PATTERN.matcher(trimmed).matches()) {
                titles.add(trimmed);
                contents.add(new StringBuilder());
            } else if (contents.isEmpty()) {
                // 首个章节标题之前的内容暂存
                if (!trimmed.isEmpty()) {
                    leading.append(trimmed).append('\n');
                }
            } else {
                contents.get(contents.size() - 1).append(trimmed).append('\n');
            }
        }
        if (titles.isEmpty()) {
            // 整篇作为单章
            StringBuilder whole = new StringBuilder();
            for (String line : lines) {
                String trimmed = line.trim();
                if (!trimmed.isEmpty()) {
                    whole.append(trimmed).append('\n');
                }
            }
            String content = whole.toString().trim();
            if (!content.isEmpty()) {
                result.add(Chapter.builder().chapterName("正文").content(content).build());
            }
            return result;
        }
        // 首章标题之前的内容并入第一章
        if (!leading.toString().trim().isEmpty()) {
            contents.get(0).insert(0, leading);
        }
        for (int i = 0; i < titles.size(); i++) {
            String content = contents.get(i).toString().trim();
            if (!content.isEmpty()) {
                result.add(
                    Chapter.builder().chapterName(titles.get(i)).content(content).build());
            }
        }
        return result;
    }

    @Getter
    @Builder
    public static class Chapter {
        private final String chapterName;
        private final String content;
    }
}