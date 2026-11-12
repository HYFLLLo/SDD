package io.github.xxyopen.novel.controller.front;

import io.github.xxyopen.novel.core.common.resp.RestResp;
import io.github.xxyopen.novel.core.constant.ApiRouterConsts;
import io.github.xxyopen.novel.dto.req.BookUploadReqDto;
import io.github.xxyopen.novel.dto.resp.BookUploadRespDto;
import io.github.xxyopen.novel.service.BookUploadService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 前台门户-电子书上传模块 API 控制器
 *
 * @author xiongxiaoyang
 * @date 2022/5/17
 */
@Tag(name = "BookUploadController", description = "前台门户-电子书上传模块")
@RestController
@RequestMapping(ApiRouterConsts.API_FRONT_RESOURCE_URL_PREFIX)
@RequiredArgsConstructor
public class BookUploadController {

    private final BookUploadService bookUploadService;

    /**
     * 电子书上传接口
     */
    @Operation(summary = "电子书上传接口")
    @PostMapping("book/upload")
    public RestResp<BookUploadRespDto> uploadBook(
        @Valid @ModelAttribute BookUploadReqDto dto) {
        return bookUploadService.uploadBook(dto);
    }

}