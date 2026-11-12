package io.github.xxyopen.novel.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import io.github.xxyopen.novel.core.auth.UserHolder;
import io.github.xxyopen.novel.core.common.constant.ErrorCodeEnum;
import io.github.xxyopen.novel.core.common.exception.BusinessException;
import io.github.xxyopen.novel.core.common.req.PageReqDto;
import io.github.xxyopen.novel.core.common.resp.PageRespDto;
import io.github.xxyopen.novel.core.common.resp.RestResp;
import io.github.xxyopen.novel.core.common.util.EpubBookParser;
import io.github.xxyopen.novel.core.common.util.TxtBookParser;
import io.github.xxyopen.novel.core.config.NovelProperties;
import io.github.xxyopen.novel.core.constant.DatabaseConsts;
import io.github.xxyopen.novel.dao.entity.BookChapter;
import io.github.xxyopen.novel.dao.entity.BookComment;
import io.github.xxyopen.novel.dao.entity.BookCommentCopy1;
import io.github.xxyopen.novel.dao.entity.BookCommentReply;
import io.github.xxyopen.novel.dao.entity.BookContent;
import io.github.xxyopen.novel.dao.entity.BookInfo;
import io.github.xxyopen.novel.dao.entity.HomeBook;
import io.github.xxyopen.novel.dao.entity.UserBookshelf;
import io.github.xxyopen.novel.dao.entity.UserInfo;
import io.github.xxyopen.novel.dao.entity.UserReadHistory;
import io.github.xxyopen.novel.dao.mapper.BookChapterMapper;
import io.github.xxyopen.novel.dao.mapper.BookCommentCopy1Mapper;
import io.github.xxyopen.novel.dao.mapper.BookCommentMapper;
import io.github.xxyopen.novel.dao.mapper.BookCommentReplyMapper;
import io.github.xxyopen.novel.dao.mapper.BookContentMapper;
import io.github.xxyopen.novel.dao.mapper.BookInfoMapper;
import io.github.xxyopen.novel.dao.mapper.HomeBookMapper;
import io.github.xxyopen.novel.dao.mapper.UserBookshelfMapper;
import io.github.xxyopen.novel.dao.mapper.UserInfoMapper;
import io.github.xxyopen.novel.dao.mapper.UserReadHistoryMapper;
import io.github.xxyopen.novel.dto.req.AdminBookContentReqDto;
import io.github.xxyopen.novel.dto.req.AdminBookCoverReqDto;
import io.github.xxyopen.novel.dto.req.AdminBookReqDto;
import io.github.xxyopen.novel.dto.req.AdminBookUpdateReqDto;
import io.github.xxyopen.novel.dto.req.UploadBookAuthorReqDto;
import io.github.xxyopen.novel.dto.req.UploadBookReqDto;
import io.github.xxyopen.novel.dto.req.UploadBookStatusReqDto;
import io.github.xxyopen.novel.dto.resp.BookChapterCountDto;
import io.github.xxyopen.novel.dto.resp.BookUploadRespDto;
import io.github.xxyopen.novel.dto.resp.UploadBookRespDto;
import io.github.xxyopen.novel.manager.cache.BookChapterCacheManager;
import io.github.xxyopen.novel.manager.cache.BookContentCacheManager;
import io.github.xxyopen.novel.manager.cache.BookInfoCacheManager;
import io.github.xxyopen.novel.manager.cache.BookRankCacheManager;
import io.github.xxyopen.novel.manager.cache.HomeBookCacheManager;
import io.github.xxyopen.novel.service.UploadService;
import java.io.IOException;
import java.time.LocalDateTime;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

/**
 * 我的上传 / 管理员书籍管理 服务实现类。
 *
 * <p>管理接口仅管理员可用；列表默认管理全站书籍，原“我的上传”继续按 uploader_id 归属当前用户。</p>
 */
@Service
@RequiredArgsConstructor
@Slf4j
@EnableConfigurationProperties(NovelProperties.class)
public class UploadServiceImpl implements UploadService {

    private static final int BOOK_NAME_MAX_LENGTH = 50;

    private static final int AUTHOR_NAME_MAX_LENGTH = 50;

    private static final int CATEGORY_NAME_MAX_LENGTH = 50;

    private static final int BOOK_DESC_MAX_LENGTH = 2000;

    private static final int CHAPTER_NAME_MAX_LENGTH = 100;

    private static final int LAST_CHAPTER_NAME_MAX_LENGTH = 50;

    private static final int PIC_URL_MAX_LENGTH = 100;

    private static final String SUPPORT_TXT_EXTENSION = "txt";

    private static final String SUPPORT_EPUB_EXTENSION = "epub";

    private final BookInfoMapper bookInfoMapper;

    private final BookChapterMapper bookChapterMapper;

    private final BookContentMapper bookContentMapper;

    private final BookCommentMapper bookCommentMapper;

    private final BookCommentCopy1Mapper bookCommentCopy1Mapper;

    private final BookCommentReplyMapper bookCommentReplyMapper;

    private final UserReadHistoryMapper userReadHistoryMapper;

    private final UserBookshelfMapper userBookshelfMapper;

    private final HomeBookMapper homeBookMapper;

    private final UserInfoMapper userInfoMapper;

    private final BookInfoCacheManager bookInfoCacheManager;

    private final BookChapterCacheManager bookChapterCacheManager;

    private final BookContentCacheManager bookContentCacheManager;

    private final HomeBookCacheManager homeBookCacheManager;

    private final BookRankCacheManager bookRankCacheManager;

    private final NovelProperties novelProperties;

    @Override
    public RestResp<PageRespDto<UploadBookRespDto>> listMyUploadBooks(UploadBookReqDto dto) {
        Long userId = getCurrentAdminUserId();

        QueryWrapper<BookInfo> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq(DatabaseConsts.BookTable.COLUMN_UPLOADER_ID, userId)
            .eq(dto.getBookStatus() != null, "book_status", dto.getBookStatus())
            .orderByDesc(DatabaseConsts.CommonColumnEnum.CREATE_TIME.getName());

        return listBooks(dto, queryWrapper);
    }

    @Override
    public RestResp<PageRespDto<UploadBookRespDto>> listAdminBooks(AdminBookReqDto dto) {
        getCurrentAdminUserId();

        QueryWrapper<BookInfo> queryWrapper = new QueryWrapper<>();
        queryWrapper.like(StringUtils.hasText(dto.getBookName()),
                DatabaseConsts.BookTable.COLUMN_BOOK_NAME, dto.getBookName())
            .eq(dto.getBookStatus() != null, "book_status", dto.getBookStatus())
            .orderByDesc(DatabaseConsts.CommonColumnEnum.UPDATE_TIME.getName());

        return listBooks(dto, queryWrapper);
    }

    @Transactional(rollbackFor = Exception.class)
    @Override
    public RestResp<Void> updateBookStatus(Long bookId, UploadBookStatusReqDto dto) {
        Long userId = getCurrentAdminUserId();

        BookInfo bookInfo = bookInfoMapper.selectById(bookId);
        if (Objects.isNull(bookInfo)
            || !Objects.equals(bookInfo.getUploaderId(), userId)) {
            throw new BusinessException(ErrorCodeEnum.BOOK_NOT_FOUND);
        }

        if (Objects.equals(bookInfo.getBookStatus(), dto.getBookStatus())) {
            return RestResp.ok();
        }

        BookInfo updateBookInfo = new BookInfo();
        updateBookInfo.setId(bookId);
        updateBookInfo.setBookStatus(dto.getBookStatus());
        updateBookInfo.setUpdateTime(LocalDateTime.now());
        bookInfoMapper.updateById(updateBookInfo);
        bookInfoCacheManager.evictBookInfoCache(bookId);
        return RestResp.ok();
    }

    @Transactional(rollbackFor = Exception.class)
    @Override
    public RestResp<Void> updateBookAuthor(Long bookId, UploadBookAuthorReqDto dto) {
        Long userId = getCurrentAdminUserId();

        BookInfo bookInfo = bookInfoMapper.selectById(bookId);
        if (Objects.isNull(bookInfo)
            || !Objects.equals(bookInfo.getUploaderId(), userId)) {
            throw new BusinessException(ErrorCodeEnum.BOOK_NOT_FOUND);
        }

        String authorName = truncate(dto.getAuthorName().trim(), AUTHOR_NAME_MAX_LENGTH);
        if (Objects.equals(bookInfo.getAuthorName(), authorName)) {
            return RestResp.ok();
        }

        BookInfo updateBookInfo = new BookInfo();
        updateBookInfo.setId(bookId);
        updateBookInfo.setAuthorName(authorName);
        updateBookInfo.setUpdateTime(LocalDateTime.now());
        bookInfoMapper.updateById(updateBookInfo);
        bookInfoCacheManager.evictBookInfoCache(bookId);
        return RestResp.ok();
    }

    @Transactional(rollbackFor = Exception.class)
    @Override
    public RestResp<Void> updateBook(Long bookId, AdminBookUpdateReqDto dto) {
        getCurrentAdminUserId();

        BookInfo bookInfo = bookInfoMapper.selectById(bookId);
        if (Objects.isNull(bookInfo)) {
            throw new BusinessException(ErrorCodeEnum.BOOK_NOT_FOUND);
        }

        String bookName = truncate(dto.getBookName().trim(), BOOK_NAME_MAX_LENGTH);
        String authorName = truncate(dto.getAuthorName().trim(), AUTHOR_NAME_MAX_LENGTH);
        checkBookNameAuthorNameUnique(bookName, authorName, bookId);

        BookInfo updateBookInfo = new BookInfo();
        updateBookInfo.setId(bookId);
        updateBookInfo.setBookName(bookName);
        updateBookInfo.setAuthorName(authorName);
        updateBookInfo.setWorkDirection(dto.getWorkDirection());
        updateBookInfo.setCategoryId(dto.getCategoryId());
        updateBookInfo.setCategoryName(truncate(dto.getCategoryName().trim(), CATEGORY_NAME_MAX_LENGTH));
        updateBookInfo.setBookDesc(truncate(
            StringUtils.hasText(dto.getBookDesc()) ? dto.getBookDesc().trim() : "",
            BOOK_DESC_MAX_LENGTH));
        updateBookInfo.setBookStatus(dto.getBookStatus());
        updateBookInfo.setUpdateTime(LocalDateTime.now());
        bookInfoMapper.updateById(updateBookInfo);
        bookInfoCacheManager.evictBookInfoCache(bookId);
        return RestResp.ok();
    }

    @Transactional(rollbackFor = Exception.class)
    @Override
    public RestResp<Void> updateBookCover(Long bookId, AdminBookCoverReqDto dto) {
        getCurrentAdminUserId();

        BookInfo bookInfo = bookInfoMapper.selectById(bookId);
        if (Objects.isNull(bookInfo)) {
            throw new BusinessException(ErrorCodeEnum.BOOK_NOT_FOUND);
        }

        String picUrl = truncate(dto.getPicUrl().trim(), PIC_URL_MAX_LENGTH);
        BookInfo updateBookInfo = new BookInfo();
        updateBookInfo.setId(bookId);
        updateBookInfo.setPicUrl(picUrl);
        updateBookInfo.setUpdateTime(LocalDateTime.now());
        bookInfoMapper.updateById(updateBookInfo);
        bookInfoCacheManager.evictBookInfoCache(bookId);
        return RestResp.ok();
    }

    @Transactional(rollbackFor = Exception.class)
    @Override
    public RestResp<BookUploadRespDto> replaceBookContent(Long bookId,
        AdminBookContentReqDto dto) {
        getCurrentAdminUserId();

        BookInfo bookInfo = bookInfoMapper.selectById(bookId);
        if (Objects.isNull(bookInfo)) {
            throw new BusinessException(ErrorCodeEnum.BOOK_NOT_FOUND);
        }

        List<TxtBookParser.Chapter> chapters = parseBookFile(dto.getFile());
        if (chapters == null || chapters.isEmpty()) {
            throw new BusinessException(ErrorCodeEnum.USER_UPLOAD_BOOK_PARSE_ERROR);
        }
        return doReplaceBookContent(bookInfo, chapters);
    }

    @Transactional(rollbackFor = Exception.class)
    @Override
    public RestResp<Void> deleteBook(Long bookId) {
        getCurrentAdminUserId();

        BookInfo bookInfo = bookInfoMapper.selectById(bookId);
        if (Objects.isNull(bookInfo)) {
            throw new BusinessException(ErrorCodeEnum.BOOK_NOT_FOUND);
        }

        List<BookChapter> oldChapters = listChapters(bookId);
        List<Long> oldChapterIds = oldChapters.stream().map(BookChapter::getId).toList();
        if (!CollectionUtils.isEmpty(oldChapterIds)) {
            bookContentMapper.delete(new QueryWrapper<BookContent>()
                .in(DatabaseConsts.BookContentTable.COLUMN_CHAPTER_ID, oldChapterIds));
            oldChapterIds.forEach(bookContentCacheManager::evictBookContentCache);
            oldChapterIds.forEach(bookChapterCacheManager::evictBookChapterCache);
        }

        bookChapterMapper.delete(new QueryWrapper<BookChapter>()
            .eq(DatabaseConsts.BookChapterTable.COLUMN_BOOK_ID, bookId));

        userReadHistoryMapper.delete(new QueryWrapper<UserReadHistory>()
            .eq(DatabaseConsts.UserReadHistoryTable.COLUMN_BOOK_ID, bookId));
        userBookshelfMapper.delete(new QueryWrapper<UserBookshelf>()
            .eq(DatabaseConsts.UserBookshelfTable.COLUMN_BOOK_ID, bookId));
        homeBookMapper.delete(new QueryWrapper<HomeBook>()
            .eq("book_id", bookId));

        deleteBookComments(bookId);
        bookInfoMapper.deleteById(bookId);
        bookInfoCacheManager.evictBookInfoCache(bookId);
        bookInfoCacheManager.evictLastUpdateIdListCache();
        homeBookCacheManager.evictHomeBookCache();
        bookRankCacheManager.evictVisitRankBooks();
        bookRankCacheManager.evictNewestRankBooks();
        bookRankCacheManager.evictUpdateRankBooks();
        return RestResp.ok();
    }

    private RestResp<PageRespDto<UploadBookRespDto>> listBooks(PageReqDto dto,
        QueryWrapper<BookInfo> queryWrapper) {
        IPage<BookInfo> page = new Page<>();
        page.setCurrent(dto.getPageNum());
        page.setSize(dto.getPageSize());
        IPage<BookInfo> bookInfoPage = bookInfoMapper.selectPage(page, queryWrapper);

        List<BookInfo> bookInfos = bookInfoPage.getRecords();
        Map<Long, Long> chapterCountMap = countChaptersByBookIds(
            bookInfos.stream().map(BookInfo::getId).toList());

        List<UploadBookRespDto> list = bookInfos.stream()
            .map(v -> UploadBookRespDto.builder()
                .id(v.getId())
                .workDirection(v.getWorkDirection())
                .categoryId(v.getCategoryId())
                .bookName(v.getBookName())
                .authorName(v.getAuthorName())
                .categoryName(v.getCategoryName())
                .picUrl(v.getPicUrl())
                .bookDesc(v.getBookDesc())
                .wordCount(v.getWordCount())
                .chapterCount(chapterCountMap.getOrDefault(v.getId(), 0L).intValue())
                .bookStatus(v.getBookStatus())
                .lastChapterName(v.getLastChapterName())
                .createTime(v.getCreateTime())
                .updateTime(v.getUpdateTime())
                .build())
            .toList();

        return RestResp.ok(PageRespDto.of(dto.getPageNum(), dto.getPageSize(),
            bookInfoPage.getTotal(), list));
    }

    private RestResp<BookUploadRespDto> doReplaceBookContent(BookInfo bookInfo,
        List<TxtBookParser.Chapter> chapters) {
        Long bookId = bookInfo.getId();
        LocalDateTime now = LocalDateTime.now();

        List<BookChapter> oldChapters = listChapters(bookId);
        List<Long> oldChapterIds = oldChapters.stream().map(BookChapter::getId).toList();
        if (!CollectionUtils.isEmpty(oldChapterIds)) {
            bookContentMapper.delete(new QueryWrapper<BookContent>()
                .in(DatabaseConsts.BookContentTable.COLUMN_CHAPTER_ID, oldChapterIds));
            oldChapterIds.forEach(bookContentCacheManager::evictBookContentCache);
            oldChapterIds.forEach(bookChapterCacheManager::evictBookChapterCache);
        }
        bookChapterMapper.delete(new QueryWrapper<BookChapter>()
            .eq(DatabaseConsts.BookChapterTable.COLUMN_BOOK_ID, bookId));
        userReadHistoryMapper.delete(new QueryWrapper<UserReadHistory>()
            .eq(DatabaseConsts.UserReadHistoryTable.COLUMN_BOOK_ID, bookId));

        int wordCount = 0;
        Long lastChapterId = null;
        String lastChapterName = null;
        LocalDateTime lastChapterUpdateTime = null;
        int index = 0;
        for (TxtBookParser.Chapter chapter : chapters) {
            BookChapter bookChapter = new BookChapter();
            bookChapter.setBookId(bookId);
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

        BookInfo updateBookInfo = new BookInfo();
        updateBookInfo.setId(bookId);
        updateBookInfo.setWordCount(wordCount);
        updateBookInfo.setLastChapterId(lastChapterId);
        updateBookInfo.setLastChapterName(lastChapterName);
        updateBookInfo.setLastChapterUpdateTime(lastChapterUpdateTime);
        updateBookInfo.setUpdateTime(now);
        bookInfoMapper.updateById(updateBookInfo);

        bookInfoCacheManager.evictBookInfoCache(bookId);
        if (Objects.nonNull(lastChapterId)) {
            bookChapterCacheManager.evictBookChapterCache(lastChapterId);
            bookContentCacheManager.evictBookContentCache(lastChapterId);
        }

        return RestResp.ok(BookUploadRespDto.builder()
            .bookId(bookId)
            .bookName(bookInfo.getBookName())
            .chapterCount(chapters.size())
            .wordCount(wordCount)
            .message("内容替换成功，共解析 " + chapters.size() + " 章")
            .build());
    }

    private List<TxtBookParser.Chapter> parseBookFile(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new BusinessException(ErrorCodeEnum.USER_UPLOAD_FILE_EMPTY);
        }
        String extension = getExtension(file.getOriginalFilename());
        if (!SUPPORT_TXT_EXTENSION.equals(extension)
            && !SUPPORT_EPUB_EXTENSION.equals(extension)) {
            throw new BusinessException(ErrorCodeEnum.USER_UPLOAD_FILE_TYPE_NOT_SUPPORT);
        }

        try {
            byte[] fileBytes = file.getBytes();
            if (SUPPORT_TXT_EXTENSION.equals(extension)) {
                String decodedText = TxtBookParser.readText(fileBytes);
                if (decodedText == null || decodedText.trim().isEmpty()
                    || TxtBookParser.isGibberish(decodedText)) {
                    throw new BusinessException(ErrorCodeEnum.USER_UPLOAD_FILE_EMPTY);
                }
                return TxtBookParser.splitChapters(TxtBookParser.cleanText(decodedText));
            }
            return EpubBookParser.parseEpub(fileBytes);
        } catch (IOException e) {
            log.error("电子书文件读取失败", e);
            throw new BusinessException(ErrorCodeEnum.USER_UPLOAD_BOOK_PARSE_ERROR);
        }
    }

    private List<BookChapter> listChapters(Long bookId) {
        return bookChapterMapper.selectList(new QueryWrapper<BookChapter>()
            .eq(DatabaseConsts.BookChapterTable.COLUMN_BOOK_ID, bookId));
    }

    private void deleteBookComments(Long bookId) {
        List<BookComment> comments = bookCommentMapper.selectList(
            new QueryWrapper<BookComment>()
                .eq(DatabaseConsts.BookCommentTable.COLUMN_BOOK_ID, bookId));
        if (!CollectionUtils.isEmpty(comments)) {
            List<Long> commentIds = comments.stream().map(BookComment::getId).toList();
            bookCommentReplyMapper.delete(new QueryWrapper<BookCommentReply>()
                .in("comment_id", commentIds));
        }
        bookCommentMapper.delete(new QueryWrapper<BookComment>()
            .eq(DatabaseConsts.BookCommentTable.COLUMN_BOOK_ID, bookId));
        bookCommentCopy1Mapper.delete(new QueryWrapper<BookCommentCopy1>()
            .eq(DatabaseConsts.BookCommentTable.COLUMN_BOOK_ID, bookId));
    }

    private void checkBookNameAuthorNameUnique(String bookName, String authorName, Long bookId) {
        QueryWrapper<BookInfo> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq(DatabaseConsts.BookTable.COLUMN_BOOK_NAME, bookName)
            .eq("author_name", authorName)
            .ne(DatabaseConsts.CommonColumnEnum.ID.getName(), bookId);
        if (bookInfoMapper.selectCount(queryWrapper) > 0) {
            throw new BusinessException(ErrorCodeEnum.USER_UPLOAD_BOOK_NAME_EXIST);
        }
    }

    private Long getCurrentAdminUserId() {
        Long userId = UserHolder.getUserId();
        if (Objects.isNull(userId)) {
            throw new BusinessException(ErrorCodeEnum.USER_UN_AUTH);
        }
        UserInfo userInfo = userInfoMapper.selectById(userId);
        NovelProperties.Admin admin = novelProperties.admin();
        if (Objects.isNull(userInfo) || Objects.isNull(admin)
            || !Objects.equals(admin.username(), userInfo.getUsername())) {
            throw new BusinessException(ErrorCodeEnum.USER_UN_AUTH);
        }
        return userId;
    }

    private Map<Long, Long> countChaptersByBookIds(List<Long> bookIds) {
        if (CollectionUtils.isEmpty(bookIds)) {
            return Collections.emptyMap();
        }
        return bookChapterMapper.countChaptersByBookIds(bookIds).stream()
            .filter(item -> Objects.nonNull(item.getBookId())
                && Objects.nonNull(item.getChapterCount()))
            .collect(Collectors.toMap(BookChapterCountDto::getBookId,
                BookChapterCountDto::getChapterCount));
    }

    private String truncate(String value, int maxLength) {
        if (value == null || maxLength < 0) {
            return value;
        }
        if (value.codePointCount(0, value.length()) <= maxLength) {
            return value;
        }
        return value.substring(0, value.offsetByCodePoints(0, maxLength));
    }

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
