package io.github.xxyopen.novel.service;

import io.github.xxyopen.novel.core.common.resp.RestResp;
import io.github.xxyopen.novel.dto.req.BookUploadReqDto;
import io.github.xxyopen.novel.dto.resp.BookUploadRespDto;

/**
 * 电子书上传 服务类
 *
 * @author xiongxiaoyang
 * @date 2022/5/17
 */
public interface BookUploadService {

    /**
     * 上传并解析电子书
     *
     * @param dto 电子书上传请求数据
     * @return 上传结果
     */
    RestResp<BookUploadRespDto> uploadBook(BookUploadReqDto dto);
}