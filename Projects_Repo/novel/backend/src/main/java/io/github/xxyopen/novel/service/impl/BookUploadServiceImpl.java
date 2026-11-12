package io.github.xxyopen.novel.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import io.github.xxyopen.novel.core.auth.UserHolder;
import io.github.xxyopen.novel.core.common.constant.ErrorCodeEnum;
import io.github.xxyopen.novel.core.common.exception.BusinessException;
import io.github.xxyopen.novel.core.common.resp.RestResp;
import io.github.xxyopen.novel.core.common.util.EpubBookParser;
import io.github.xxyopen.novel.core.common.util.TxtBookParser;
import io.github.xxyopen.novel.core.constant.DatabaseConsts;
import io.github.xxyopen.novel.dao.entity.BookChapter;
import io.github.xxyopen.novel.dao.entity.BookContent;
import io.github.xxyopen.novel.dao.entity.BookInfo;
import io.github.xxyopen.novel.dao.mapper.BookChapterMapper;
import io.github.xxyopen.novel.dao.mapper.BookContentMapper;
import io.github.xxyopen.novel.dao.mapper.BookInfoMapper;
import io.github.xxyopen.novel.dto.req.BookUploadReqDto;
import io.github.xxyopen.novel.dto.resp.BookUploadRespDto;
import io.github.xxyopen.novel.manager.cache.BookChapterCacheManager;
import io.github.xxyopen.novel.manager.cache.BookContentCacheManager;
import io.github.xxyopen.novel.manager.cache.BookInfoCacheManager;
import io.github.xxyopen.novel.service.BookUploadService;
import java.io.IOException;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Locale;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

/**
 * 电子书上传 服务实现类。
 * <p>
 * 前台免登录上传：author_id 固定为 0（匿名），author_name 取表单值（默认「匿名用户」）。
 * 整本上传（建书 + 全量章节）作为单个事务，任一步失败整体回滚，不产生半本书。
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class BookUploadServiceImpl implements BookUploadService {

    private final BookInfoMapper bookInfoMapper;

    private final BookChapterMapper bookChapterMapper;

    private final BookContentMapper bookContentMapper;

    private final BookInfoCacheManager bookInfoCacheManager;

    private final BookChapterCacheManager bookChapterCacheManager;

    private final BookContentCacheManager bookContentCacheManager;

    /** 匿名作者的 author_id */
    private static final Long ANONYMOUS_AUTHOR_ID = 0L;

    /** 作者名为空时的默认名 */
    private static final String CREATE_BY_SYSTEM = "匿名用户";

    /** 数据库字段最大字符数，用于入库前截断，避免超长字段触发 Data truncation */
    private static final int BOOK_NAME_MAX_LENGTH = 50;

    private static final int AUTHOR_NAME_MAX_LENGTH = 50;

    private static final int CATEGORY_NAME_MAX_LENGTH = 50;

    private static final int BOOK_DESC_MAX_LENGTH = 2000;

    private static final int CHAPTER_NAME_MAX_LENGTH = 100;

    private static final int LAST_CHAPTER_NAME_MAX_LENGTH = 50;

    /** 支持的上传文件扩展名 */
    private static final String SUPPORT_TXT_EXTENSION = "txt";
    private static final String SUPPORT_EPUB_EXTENSION = "epub";

    @Override
    @Transactional(rollbackFor = Exception.class)
    public RestResp<BookUploadRespDto> uploadBook(BookUploadReqDto dto) {
        MultipartFile file = dto.getFile();
        // 1. 空文件校验
        if (file == null || file.isEmpty()) {
            throw new BusinessException(ErrorCodeEnum.USER_UPLOAD_FILE_EMPTY);
        }
        // 2. 格式校验（仅 .txt / .epub）
        String extension = getExtension(file.getOriginalFilename());
        if (!SUPPORT_TXT_EXTENSION.equals(extension)
            && !SUPPORT_EPUB_EXTENSION.equals(extension)) {
            throw new BusinessException(ErrorCodeEnum.USER_UPLOAD_FILE_TYPE_NOT_SUPPORT);
        }
        // 3. 编码识别 + 解析文本
        List<TxtBookParser.Chapter> chapters;
        try {
            byte[] fileBytes = file.getBytes();
            if (SUPPORT_TXT_EXTENSION.equals(extension)) {
                String decodedText = TxtBookParser.readText(fileBytes);
                // 3.1 空文件 / 二进制内容伪装成 txt → A0706
                if (decodedText == null || decodedText.trim().isEmpty()
                    || TxtBookParser.isGibberish(decodedText)) {
                    throw new BusinessException(ErrorCodeEnum.USER_UPLOAD_FILE_EMPTY);
                }
                chapters = TxtBookParser.splitChapters(TxtBookParser.cleanText(decodedText));
            } else {
                // 3.2 epub 解析：zip 损坏 / 缺 container.xml / OPF 结构不完整 / 无有效章节 → 空列表 → A0704
                chapters = EpubBookParser.parseEpub(fileBytes);
            }
        } catch (IOException e) {
            log.error("电子书文件读取失败", e);
            throw new BusinessException(ErrorCodeEnum.USER_UPLOAD_BOOK_PARSE_ERROR);
        }
        // 4. 解析后无有效章节 → A0704
        if (chapters == null || chapters.isEmpty()) {
            throw new BusinessException(ErrorCodeEnum.USER_UPLOAD_BOOK_PARSE_ERROR);
        }
        // 5. 校验同名书是否存在（author_id=0 下查 book_name）
        String bookName = dto.getBookName();
        QueryWrapper<BookInfo> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq(DatabaseConsts.BookTable.COLUMN_BOOK_NAME, bookName)
            .eq(DatabaseConsts.BookTable.AUTHOR_ID, ANONYMOUS_AUTHOR_ID);
        if (bookInfoMapper.selectCount(queryWrapper) > 0) {
            throw new BusinessException(ErrorCodeEnum.USER_UPLOAD_BOOK_NAME_EXIST);
        }
        // 6. 单事务入库
        return doUploadBook(dto, chapters);
    }

    /**
     * 执行建书 + 逐章入库 + 更新 book_info 最新章节/字数。
     *
     * @param dto      上传表单
     * @param chapters 已解析的章节列表
     * @return 上传结果
     */
    private RestResp<BookUploadRespDto> doUploadBook(BookUploadReqDto dto,
        List<TxtBookParser.Chapter> chapters) {
        // 6.1 建书
        LocalDateTime now = LocalDateTime.now();
        BookInfo bookInfo = new BookInfo();
        bookInfo.setWorkDirection(dto.getWorkDirection());
        bookInfo.setCategoryId(dto.getCategoryId());
        bookInfo.setCategoryName(truncate(dto.getCategoryName(), CATEGORY_NAME_MAX_LENGTH));
        // book_name 列 NOT NULL 无默认值；前端必填，但防绑定漏带/空白 → 兜底为占位名（同名校验在前已兜）
        String bookName = StringUtils.hasText(dto.getBookName()) ? dto.getBookName().trim()
            : ("未命名书籍-" + now.format(java.time.format.DateTimeFormatter.ofPattern("yyyyMMddHHmmss")));
        bookInfo.setBookName(truncate(bookName, BOOK_NAME_MAX_LENGTH));
        bookInfo.setAuthorId(ANONYMOUS_AUTHOR_ID);
        // 上传归属：登录态取 UserHolder 用户 id，未登录（token 缺失/解析失败为 null）落 0（匿名）
        Long uploaderId = UserHolder.getUserId();
        bookInfo.setUploaderId(uploaderId == null ? 0L : uploaderId);
        String authorName = StringUtils.hasText(dto.getAuthorName())
            ? dto.getAuthorName().trim() : CREATE_BY_SYSTEM;
        bookInfo.setAuthorName(truncate(authorName, AUTHOR_NAME_MAX_LENGTH));
        // book_desc 列 NOT NULL 无默认值，留空时传空串兜底（避免 Field 'book_desc' doesn't have a default value）
        bookInfo.setBookDesc(
            truncate(StringUtils.hasText(dto.getBookDesc()) ? dto.getBookDesc().trim() : "",
                BOOK_DESC_MAX_LENGTH));
        // 默认封面：resources/static/img/default-cover.gif，随 jar 打包，经 Spring 静态资源映射可访问（不用 /image/**）
        bookInfo.setPicUrl("/img/default-cover.gif");
        bookInfo.setBookStatus(0);
        bookInfo.setVisitCount(0L);
        bookInfo.setWordCount(0);
        bookInfo.setCommentCount(0);
        bookInfo.setIsVip(0);
        bookInfo.setScore(0);
        bookInfo.setCreateTime(now);
        bookInfo.setUpdateTime(now);
        bookInfoMapper.insert(bookInfo);

        // 6.2 逐章写入
        int wordCount = 0;
        Long lastChapterId = null;
        String lastChapterName = null;
        LocalDateTime lastChapterUpdateTime = null;
        int index = 0;
        for (TxtBookParser.Chapter chapter : chapters) {
            BookChapter bookChapter = new BookChapter();
            bookChapter.setBookId(bookInfo.getId());
            bookChapter.setChapterNum(index++);
            bookChapter.setChapterName(truncate(chapter.getChapterName(), CHAPTER_NAME_MAX_LENGTH));
            bookChapter.setWordCount(chapter.getContent().length());
            bookChapter.setIsVip(0);
            bookChapter.setCreateTime(now);
            bookChapter.setUpdateTime(now);
            bookChapterMapper.insert(bookChapter);

            BookContent bookContent = new BookContent();
            bookContent.setChapterId(bookChapter.getId());
            bookContent.setContent(chapter.getContent());
            bookContent.setCreateTime(now);
            bookContent.setUpdateTime(now);
            bookContentMapper.insert(bookContent);

            wordCount += bookChapter.getWordCount();
            lastChapterId = bookChapter.getId();
            lastChapterName = truncate(bookChapter.getChapterName(), LAST_CHAPTER_NAME_MAX_LENGTH);
            lastChapterUpdateTime = now;
        }

        // 6.3 更新 book_info
        BookInfo updateBookInfo = new BookInfo();
        updateBookInfo.setId(bookInfo.getId());
        updateBookInfo.setWordCount(wordCount);
        updateBookInfo.setLastChapterId(lastChapterId);
        updateBookInfo.setLastChapterName(lastChapterName);
        updateBookInfo.setLastChapterUpdateTime(lastChapterUpdateTime);
        updateBookInfo.setUpdateTime(now);
        bookInfoMapper.updateById(updateBookInfo);

        // 6.4 清理缓存
        bookInfoCacheManager.evictBookInfoCache(bookInfo.getId());
        bookChapterCacheManager.evictBookChapterCache(lastChapterId);
        bookContentCacheManager.evictBookContentCache(lastChapterId);

        return RestResp.ok(BookUploadRespDto.builder()
            .bookId(bookInfo.getId())
            .bookName(bookInfo.getBookName())
            .chapterCount(chapters.size())
            .wordCount(wordCount)
            .message("上传成功，共解析 " + chapters.size() + " 章")
            .build());
    }

    /**
     * 按数据库字段最大字符数截断字符串（按 Unicode code point 计数，避免切断 emoji 等代理对）。
     *
     * @param value     原字符串
     * @param maxLength 最大字符数
     * @return 截断后的字符串；未超长时返回原值
     */
    private String truncate(String value, int maxLength) {
        if (value == null || maxLength < 0) {
            return value;
        }
        if (value.codePointCount(0, value.length()) <= maxLength) {
            return value;
        }
        return value.substring(0, value.offsetByCodePoints(0, maxLength));
    }

    /**
     * 提取文件名扩展名（小写，含小圆点后第一个字符开始）。
     */
    private String getExtension(String fileName) {
        if (!StringUtils.hasText(fileName)) {
            return "";
        }
        int dotIndex = fileName.lastIndexOf('.');
        if (dotIndex < 0 || dotIndex == fileName.length() - 1) {
            return "";
        }
        return fileName.substring(dotIndex + 1).toLowerCase(Locale.ROOT);
    }
}
