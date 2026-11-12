package io.github.xxyopen.novel.service;

import io.github.xxyopen.novel.core.common.resp.RestResp;
import io.github.xxyopen.novel.core.common.req.PageReqDto;
import io.github.xxyopen.novel.core.common.resp.PageRespDto;
import io.github.xxyopen.novel.dto.req.UserInfoUptReqDto;
import io.github.xxyopen.novel.dto.req.UserLoginReqDto;
import io.github.xxyopen.novel.dto.req.UserRegisterReqDto;
import io.github.xxyopen.novel.dto.resp.UserInfoRespDto;
import io.github.xxyopen.novel.dto.resp.UserLoginRespDto;
import io.github.xxyopen.novel.dto.resp.UserReadHistoryRespDto;
import io.github.xxyopen.novel.dto.resp.UserRegisterRespDto;

/**
 * 会员模块 服务类
 *
 * @author xiongxiaoyang
 * @date 2022/5/17
 */
public interface UserService {

    /**
     * 用户注册
     *
     * @param dto 注册参数
     * @return JWT
     */
    RestResp<UserRegisterRespDto> register(UserRegisterReqDto dto);

    /**
     * 用户登录
     *
     * @param dto 登录参数
     * @return JWT + 昵称
     */
    RestResp<UserLoginRespDto> login(UserLoginReqDto dto);

    /**
     * 用户反馈
     *
     * @param userId  反馈用户ID
     * @param content 反馈内容
     * @return void
     */
    RestResp<Void> saveFeedback(Long userId, String content);

    /**
     * 用户信息修改
     *
     * @param dto 用户信息
     * @return void
     */
    RestResp<Void> updateUserInfo(UserInfoUptReqDto dto);

    /**
     * 用户反馈删除
     *
     * @param userId 用户ID
     * @param id     反馈ID
     * @return void
     */
    RestResp<Void> deleteFeedback(Long userId, Long id);

    /**
     * 查询书架状态接口
     *
     * @param userId 用户ID
     * @param bookId 小说ID
     * @return 0-不在书架 1-已在书架
     */
    RestResp<Integer> getBookshelfStatus(Long userId, String bookId);

    /**
     * 保存用户阅读进度
     *
     * @param userId    用户ID
     * @param bookId    小说ID
     * @param chapterId 章节ID
     * @return void
     */
    RestResp<Void> saveReadHistory(Long userId, Long bookId, Long chapterId);

    /**
     * 查询用户阅读进度
     *
     * @param userId 用户ID
     * @param bookId 小说ID
     * @return 上次阅读的章节ID；无记录时返回 null
     */
    RestResp<Long> getReadHistory(Long userId, Long bookId);

    /**
     * 分页查询用户阅读历史
     *
     * @param userId     用户ID
     * @param pageReqDto 分页请求参数
     * @return 阅读历史分页列表
     */
    RestResp<PageRespDto<UserReadHistoryRespDto>> listReadHistory(Long userId, PageReqDto pageReqDto);

    /**
     * 用户信息查询
     * @param userId 用户ID
     * @return 用户信息
     */
    RestResp<UserInfoRespDto> getUserInfo(Long userId);
}
