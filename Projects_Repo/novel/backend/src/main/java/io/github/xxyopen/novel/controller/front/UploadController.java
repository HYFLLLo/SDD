package io.github.xxyopen.novel.controller.front;

import io.github.xxyopen.novel.core.common.resp.PageRespDto;
import io.github.xxyopen.novel.core.common.resp.RestResp;
import io.github.xxyopen.novel.core.constant.ApiRouterConsts;
import io.github.xxyopen.novel.dto.req.AdminBookContentReqDto;
import io.github.xxyopen.novel.dto.req.AdminBookCoverReqDto;
import io.github.xxyopen.novel.dto.req.AdminBookReqDto;
import io.github.xxyopen.novel.dto.req.AdminBookUpdateReqDto;
import io.github.xxyopen.novel.dto.req.UploadBookAuthorReqDto;
import io.github.xxyopen.novel.dto.req.UploadBookReqDto;
import io.github.xxyopen.novel.dto.req.UploadBookStatusReqDto;
import io.github.xxyopen.novel.dto.resp.BookUploadRespDto;
import io.github.xxyopen.novel.dto.resp.UploadBookRespDto;
import io.github.xxyopen.novel.service.UploadService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 前台门户-我的上传模块 API 控制器
 *
 * @author xiongxiaoyang
 * @date 2026/10/21
 */
@Tag(name = "UploadController", description = "前台门户-我的上传模块")
@RestController
@RequestMapping(ApiRouterConsts.API_FRONT_UPLOAD_URL_PREFIX)
@RequiredArgsConstructor
public class UploadController {

    private final UploadService uploadService;

    /**
     * 我的上传分页列表查询接口
     */
    @Operation(summary = "我的上传分页列表查询接口")
    @GetMapping("books")
    public RestResp<PageRespDto<UploadBookRespDto>> listMyUploadBooks(UploadBookReqDto dto) {
        return uploadService.listMyUploadBooks(dto);
    }

    /**
     * 管理员全站书籍分页列表查询接口
     */
    @Operation(summary = "管理员全站书籍分页列表查询接口")
    @GetMapping("books/admin")
    public RestResp<PageRespDto<UploadBookRespDto>> listAdminBooks(AdminBookReqDto dto) {
        return uploadService.listAdminBooks(dto);
    }

    /**
     * 管理员修改书籍基础信息接口
     */
    @Operation(summary = "管理员修改书籍基础信息接口")
    @PutMapping("book/{bookId}")
    public RestResp<Void> updateBook(
        @Parameter(description = "图书ID") @PathVariable("bookId") Long bookId,
        @Valid @RequestBody AdminBookUpdateReqDto dto) {
        return uploadService.updateBook(bookId, dto);
    }

    /**
     * 管理员修改书籍封面接口
     */
    @Operation(summary = "管理员修改书籍封面接口")
    @PutMapping("book/{bookId}/pic")
    public RestResp<Void> updateBookCover(
        @Parameter(description = "图书ID") @PathVariable("bookId") Long bookId,
        @Valid @RequestBody AdminBookCoverReqDto dto) {
        return uploadService.updateBookCover(bookId, dto);
    }

    /**
     * 管理员替换书籍内容接口
     */
    @Operation(summary = "管理员替换书籍内容接口")
    @PostMapping("book/{bookId}/content")
    public RestResp<BookUploadRespDto> replaceBookContent(
        @Parameter(description = "图书ID") @PathVariable("bookId") Long bookId,
        @Valid @ModelAttribute AdminBookContentReqDto dto) {
        return uploadService.replaceBookContent(bookId, dto);
    }

    /**
     * 管理员删除书籍接口
     */
    @Operation(summary = "管理员删除书籍接口")
    @DeleteMapping("book/{bookId}")
    public RestResp<Void> deleteBook(
        @Parameter(description = "图书ID") @PathVariable("bookId") Long bookId) {
        return uploadService.deleteBook(bookId);
    }

    /**
     * 切换图书状态接口
     */
    @Operation(summary = "切换图书状态接口")
    @PutMapping("book/{bookId}/status")
    public RestResp<Void> updateBookStatus(
        @Parameter(description = "图书ID") @PathVariable("bookId") Long bookId,
        @Valid @RequestBody UploadBookStatusReqDto dto) {
        return uploadService.updateBookStatus(bookId, dto);
    }

    /**
     * 修改图书作者名接口
     */
    @Operation(summary = "修改图书作者名接口")
    @PutMapping("book/{bookId}/author")
    public RestResp<Void> updateBookAuthor(
        @Parameter(description = "图书ID") @PathVariable("bookId") Long bookId,
        @Valid @RequestBody UploadBookAuthorReqDto dto) {
        return uploadService.updateBookAuthor(bookId, dto);
    }
}
