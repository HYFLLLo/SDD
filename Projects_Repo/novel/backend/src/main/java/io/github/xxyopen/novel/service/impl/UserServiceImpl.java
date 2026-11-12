package io.github.xxyopen.novel.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import io.github.xxyopen.novel.core.common.constant.CommonConsts;
import io.github.xxyopen.novel.core.common.constant.ErrorCodeEnum;
import io.github.xxyopen.novel.core.common.exception.BusinessException;
import io.github.xxyopen.novel.core.common.req.PageReqDto;
import io.github.xxyopen.novel.core.common.resp.PageRespDto;
import io.github.xxyopen.novel.core.common.resp.RestResp;
import io.github.xxyopen.novel.core.config.NovelProperties;
import io.github.xxyopen.novel.core.constant.DatabaseConsts;
import io.github.xxyopen.novel.core.constant.SystemConfigConsts;
import io.github.xxyopen.novel.core.util.JwtUtils;
import io.github.xxyopen.novel.dao.entity.BookChapter;
import io.github.xxyopen.novel.dao.entity.BookContent;
import io.github.xxyopen.novel.dao.entity.BookInfo;
import io.github.xxyopen.novel.dao.entity.UserBookshelf;
import io.github.xxyopen.novel.dao.entity.UserFeedback;
import io.github.xxyopen.novel.dao.entity.UserInfo;
import io.github.xxyopen.novel.dao.entity.UserReadHistory;
import io.github.xxyopen.novel.dao.mapper.BookChapterMapper;
import io.github.xxyopen.novel.dao.mapper.BookContentMapper;
import io.github.xxyopen.novel.dao.mapper.BookInfoMapper;
import io.github.xxyopen.novel.dao.mapper.UserBookshelfMapper;
import io.github.xxyopen.novel.dao.mapper.UserFeedbackMapper;
import io.github.xxyopen.novel.dao.mapper.UserInfoMapper;
import io.github.xxyopen.novel.dao.mapper.UserReadHistoryMapper;
import io.github.xxyopen.novel.dto.req.UserInfoUptReqDto;
import io.github.xxyopen.novel.dto.req.UserLoginReqDto;
import io.github.xxyopen.novel.dto.req.UserRegisterReqDto;
import io.github.xxyopen.novel.dto.resp.UserInfoRespDto;
import io.github.xxyopen.novel.dto.resp.UserLoginRespDto;
import io.github.xxyopen.novel.dto.resp.UserReadHistoryRespDto;
import io.github.xxyopen.novel.dto.resp.UserRegisterRespDto;
import io.github.xxyopen.novel.manager.redis.VerifyCodeManager;
import io.github.xxyopen.novel.service.UserService;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.function.Function;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.DigestUtils;

/**
 * 会员模块 服务实现类
 *
 * @author xiongxiaoyang
 * @date 2022/5/17
 */
@Service
@RequiredArgsConstructor
@EnableConfigurationProperties(NovelProperties.class)
public class UserServiceImpl implements UserService {

    private final UserInfoMapper userInfoMapper;

    private final VerifyCodeManager verifyCodeManager;

    private final UserFeedbackMapper userFeedbackMapper;

    private final UserBookshelfMapper userBookshelfMapper;

    private final UserReadHistoryMapper userReadHistoryMapper;

    private final BookContentMapper bookContentMapper;

    private final BookChapterMapper bookChapterMapper;

    private final BookInfoMapper bookInfoMapper;

    private final JwtUtils jwtUtils;

    private final NovelProperties novelProperties;

    @Override
    public RestResp<UserRegisterRespDto> register(UserRegisterReqDto dto) {
        // 校验图形验证码是否正确
        if (!verifyCodeManager.imgVerifyCodeOk(dto.getSessionId(), dto.getVelCode())) {
            // 图形验证码校验失败
            throw new BusinessException(ErrorCodeEnum.USER_VERIFY_CODE_ERROR);
        }

        // 校验手机号是否已注册
        QueryWrapper<UserInfo> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq(DatabaseConsts.UserInfoTable.COLUMN_USERNAME, dto.getUsername())
            .last(DatabaseConsts.SqlEnum.LIMIT_1.getSql());
        if (userInfoMapper.selectCount(queryWrapper) > 0) {
            // 手机号已注册
            throw new BusinessException(ErrorCodeEnum.USER_NAME_EXIST);
        }

        // 注册成功，保存用户信息
        UserInfo userInfo = new UserInfo();
        userInfo.setPassword(
            DigestUtils.md5DigestAsHex(dto.getPassword().getBytes(StandardCharsets.UTF_8)));
        userInfo.setUsername(dto.getUsername());
        userInfo.setNickName(dto.getUsername());
        userInfo.setCreateTime(LocalDateTime.now());
        userInfo.setUpdateTime(LocalDateTime.now());
        userInfo.setSalt("0");
        userInfoMapper.insert(userInfo);

        // 删除验证码
        verifyCodeManager.removeImgVerifyCode(dto.getSessionId());

        // 生成JWT 并返回
        return RestResp.ok(
            UserRegisterRespDto.builder()
                .token(jwtUtils.generateToken(userInfo.getId(), SystemConfigConsts.NOVEL_FRONT_KEY))
                .uid(userInfo.getId())
                .build()
        );

    }

    @Override
    public RestResp<UserLoginRespDto> login(UserLoginReqDto dto) {
        // 查询用户信息
        QueryWrapper<UserInfo> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq(DatabaseConsts.UserInfoTable.COLUMN_USERNAME, dto.getUsername())
            .last(DatabaseConsts.SqlEnum.LIMIT_1.getSql());
        UserInfo userInfo = userInfoMapper.selectOne(queryWrapper);
        if (Objects.isNull(userInfo)) {
            // 用户不存在
            throw new BusinessException(ErrorCodeEnum.USER_ACCOUNT_NOT_EXIST);
        }

        // 判断密码是否正确
        if (!Objects.equals(userInfo.getPassword()
            , DigestUtils.md5DigestAsHex(dto.getPassword().getBytes(StandardCharsets.UTF_8)))) {
            // 密码错误
            throw new BusinessException(ErrorCodeEnum.USER_PASSWORD_ERROR);
        }

        // 登录成功，生成JWT并返回
        return RestResp.ok(UserLoginRespDto.builder()
            .token(jwtUtils.generateToken(userInfo.getId(), SystemConfigConsts.NOVEL_FRONT_KEY))
            .uid(userInfo.getId())
            .nickName(userInfo.getNickName())
            .admin(isAdmin(userInfo.getUsername()))
            .build());
    }

    /**
     * 判断当前用户名是否为配置的管理员账号名。
     *
     * @param username 用户名
     * @return true 表示管理员
     */
    private Boolean isAdmin(String username) {
        NovelProperties.Admin admin = novelProperties.admin();
        return admin != null && Objects.equals(admin.username(), username);
    }

    @Override
    public RestResp<Void> saveFeedback(Long userId, String content) {
        UserFeedback userFeedback = new UserFeedback();
        userFeedback.setUserId(userId);
        userFeedback.setContent(content);
        userFeedback.setCreateTime(LocalDateTime.now());
        userFeedback.setUpdateTime(LocalDateTime.now());
        userFeedbackMapper.insert(userFeedback);
        return RestResp.ok();
    }

    @Override
    public RestResp<Void> updateUserInfo(UserInfoUptReqDto dto) {
        UserInfo userInfo = new UserInfo();
        userInfo.setId(dto.getUserId());
        userInfo.setNickName(dto.getNickName());
        userInfo.setUserPhoto(dto.getUserPhoto());
        userInfo.setUserSex(dto.getUserSex());
        userInfoMapper.updateById(userInfo);
        return RestResp.ok();
    }

    @Override
    public RestResp<Void> deleteFeedback(Long userId, Long id) {
        QueryWrapper<UserFeedback> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq(DatabaseConsts.CommonColumnEnum.ID.getName(), id)
            .eq(DatabaseConsts.UserFeedBackTable.COLUMN_USER_ID, userId);
        userFeedbackMapper.delete(queryWrapper);
        return RestResp.ok();
    }

    @Override
    public RestResp<Integer> getBookshelfStatus(Long userId, String bookId) {
        QueryWrapper<UserBookshelf> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq(DatabaseConsts.UserBookshelfTable.COLUMN_USER_ID, userId)
            .eq(DatabaseConsts.UserBookshelfTable.COLUMN_BOOK_ID, bookId);
        return RestResp.ok(
            userBookshelfMapper.selectCount(queryWrapper) > 0
                ? CommonConsts.YES
                : CommonConsts.NO
        );
    }

    @Transactional(rollbackFor = Exception.class)
    @Override
    public RestResp<Void> saveReadHistory(Long userId, Long bookId, Long chapterId) {
        QueryWrapper<BookContent> contentQueryWrapper = new QueryWrapper<>();
        contentQueryWrapper.eq(DatabaseConsts.BookContentTable.COLUMN_CHAPTER_ID, chapterId)
            .last(DatabaseConsts.SqlEnum.LIMIT_1.getSql());
        BookContent bookContent = bookContentMapper.selectOne(contentQueryWrapper);
        if (Objects.isNull(bookContent)) {
            return RestResp.fail(ErrorCodeEnum.BOOK_NOT_FOUND);
        }

        LocalDateTime now = LocalDateTime.now();
        QueryWrapper<UserReadHistory> historyQueryWrapper = new QueryWrapper<>();
        historyQueryWrapper.eq(DatabaseConsts.UserReadHistoryTable.COLUMN_USER_ID, userId)
            .eq(DatabaseConsts.UserReadHistoryTable.COLUMN_BOOK_ID, bookId)
            .last(DatabaseConsts.SqlEnum.LIMIT_1.getSql());
        UserReadHistory readHistory = userReadHistoryMapper.selectOne(historyQueryWrapper);
        if (Objects.isNull(readHistory)) {
            readHistory = new UserReadHistory();
            readHistory.setUserId(userId);
            readHistory.setBookId(bookId);
            readHistory.setPreContentId(bookContent.getId());
            readHistory.setCreateTime(now);
            readHistory.setUpdateTime(now);
            userReadHistoryMapper.insert(readHistory);
        } else {
            UserReadHistory update = new UserReadHistory();
            update.setId(readHistory.getId());
            update.setPreContentId(bookContent.getId());
            update.setUpdateTime(now);
            userReadHistoryMapper.updateById(update);
        }
        return RestResp.ok();
    }

    @Override
    public RestResp<Long> getReadHistory(Long userId, Long bookId) {
        QueryWrapper<UserReadHistory> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq(DatabaseConsts.UserReadHistoryTable.COLUMN_USER_ID, userId)
            .eq(DatabaseConsts.UserReadHistoryTable.COLUMN_BOOK_ID, bookId)
            .last(DatabaseConsts.SqlEnum.LIMIT_1.getSql());
        UserReadHistory readHistory = userReadHistoryMapper.selectOne(queryWrapper);
        if (Objects.isNull(readHistory)) {
            return RestResp.ok(null);
        }

        BookContent bookContent = bookContentMapper.selectById(readHistory.getPreContentId());
        if (Objects.isNull(bookContent)) {
            return RestResp.ok(null);
        }
        return RestResp.ok(bookContent.getChapterId());
    }

    @Override
    public RestResp<PageRespDto<UserReadHistoryRespDto>> listReadHistory(Long userId, PageReqDto pageReqDto) {
        IPage<UserReadHistory> page = new Page<>();
        page.setCurrent(pageReqDto.getPageNum());
        page.setSize(pageReqDto.getPageSize());
        QueryWrapper<UserReadHistory> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq(DatabaseConsts.UserReadHistoryTable.COLUMN_USER_ID, userId)
            .orderByDesc(DatabaseConsts.CommonColumnEnum.UPDATE_TIME.getName());
        IPage<UserReadHistory> historyPage = userReadHistoryMapper.selectPage(page, queryWrapper);
        List<UserReadHistory> histories = historyPage.getRecords();

        List<UserReadHistoryRespDto> historyRespList = Collections.emptyList();
        if (!histories.isEmpty()) {
            List<Long> contentIds = histories.stream().map(UserReadHistory::getPreContentId).toList();
            Map<Long, BookContent> contentMap = bookContentMapper.selectBatchIds(contentIds).stream()
                .collect(Collectors.toMap(BookContent::getId, Function.identity()));

            List<Long> chapterIds = contentMap.values().stream().map(BookContent::getChapterId).toList();
            Map<Long, BookChapter> chapterMap = chapterIds.isEmpty() ? Collections.emptyMap()
                : bookChapterMapper.selectBatchIds(chapterIds).stream()
                    .collect(Collectors.toMap(BookChapter::getId, Function.identity()));

            List<Long> bookIds = histories.stream().map(UserReadHistory::getBookId).toList();
            Map<Long, BookInfo> bookInfoMap = bookInfoMapper.selectBatchIds(bookIds).stream()
                .collect(Collectors.toMap(BookInfo::getId, Function.identity()));

            historyRespList = histories.stream().map(history -> {
                BookInfo bookInfo = bookInfoMap.get(history.getBookId());
                BookContent bookContent = contentMap.get(history.getPreContentId());
                BookChapter bookChapter = Objects.nonNull(bookContent)
                    ? chapterMap.get(bookContent.getChapterId()) : null;
                return UserReadHistoryRespDto.builder()
                    .bookId(history.getBookId())
                    .bookName(Objects.nonNull(bookInfo) ? bookInfo.getBookName() : null)
                    .picUrl(Objects.nonNull(bookInfo) ? bookInfo.getPicUrl() : null)
                    .authorName(Objects.nonNull(bookInfo) ? bookInfo.getAuthorName() : null)
                    .chapterId(Objects.nonNull(bookContent) ? bookContent.getChapterId() : null)
                    .chapterName(Objects.nonNull(bookChapter) ? bookChapter.getChapterName() : null)
                    .updateTime(history.getUpdateTime())
                    .build();
            }).toList();
        }

        return RestResp.ok(PageRespDto.of(pageReqDto.getPageNum(), pageReqDto.getPageSize(),
            historyPage.getTotal(), historyRespList));
    }

    @Override
    public RestResp<UserInfoRespDto> getUserInfo(Long userId) {
        UserInfo userInfo = userInfoMapper.selectById(userId);
        return RestResp.ok(UserInfoRespDto.builder()
            .nickName(userInfo.getNickName())
            .userSex(userInfo.getUserSex())
            .userPhoto(userInfo.getUserPhoto())
            .build());
    }
}
