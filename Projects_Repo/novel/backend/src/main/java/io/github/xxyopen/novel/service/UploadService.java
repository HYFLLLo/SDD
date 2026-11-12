package io.github.xxyopen.novel.service;

import io.github.xxyopen.novel.core.common.resp.PageRespDto;
import io.github.xxyopen.novel.core.common.resp.RestResp;
import io.github.xxyopen.novel.dto.req.AdminBookContentReqDto;
import io.github.xxyopen.novel.dto.req.AdminBookCoverReqDto;
import io.github.xxyopen.novel.dto.req.AdminBookReqDto;
import io.github.xxyopen.novel.dto.req.AdminBookUpdateReqDto;
import io.github.xxyopen.novel.dto.req.UploadBookAuthorReqDto;
import io.github.xxyopen.novel.dto.req.UploadBookReqDto;
import io.github.xxyopen.novel.dto.req.UploadBookStatusReqDto;
import io.github.xxyopen.novel.dto.resp.BookUploadRespDto;
import io.github.xxyopen.novel.dto.resp.UploadBookRespDto;

/**
 * 我的上传 服务类
 *
 * @author xiongxiaoyang
 * @date 2026/10/21
 */
public interface UploadService {

    /**
     * 分页查询当前管理员上传的图书
     *
     * @param dto 分页及筛选请求参数
     * @return 图书分页列表
     */
    RestResp<PageRespDto<UploadBookRespDto>> listMyUploadBooks(UploadBookReqDto dto);

    /**
     * 分页查询全站书籍（管理员）
     *
     * @param dto 分页及筛选请求参数
     * @return 图书分页列表
     */
    RestResp<PageRespDto<UploadBookRespDto>> listAdminBooks(AdminBookReqDto dto);

    /**
     * 切换图书状态
     *
     * @param bookId 图书ID
     * @param dto    目标状态请求参数
     * @return void
     */
    RestResp<Void> updateBookStatus(Long bookId, UploadBookStatusReqDto dto);

    /**
     * 修改图书作者名
     *
     * @param bookId 图书ID
     * @param dto    作者名请求参数
     * @return void
     */
    RestResp<Void> updateBookAuthor(Long bookId, UploadBookAuthorReqDto dto);

    /**
     * 修改书籍基础信息（管理员）
     *
     * @param bookId 图书ID
     * @param dto 基础信息请求参数
     * @return void
     */
    RestResp<Void> updateBook(Long bookId, AdminBookUpdateReqDto dto);

    /**
     * 修改书籍封面（管理员）
     *
     * @param bookId 图书ID
     * @param dto 封面请求参数
     * @return void
     */
    RestResp<Void> updateBookCover(Long bookId, AdminBookCoverReqDto dto);

    /**
     * 用最新文件替换书籍全部内容（管理员）
     *
     * @param bookId 图书ID
     * @param dto 电子书文件请求参数
     * @return 替换结果
     */
    RestResp<BookUploadRespDto> replaceBookContent(Long bookId, AdminBookContentReqDto dto);

    /**
     * 删除书籍（管理员）
     *
     * @param bookId 图书ID
     * @return void
     */
    RestResp<Void> deleteBook(Long bookId);
}
