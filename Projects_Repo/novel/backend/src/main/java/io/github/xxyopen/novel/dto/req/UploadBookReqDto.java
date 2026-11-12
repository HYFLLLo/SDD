package io.github.xxyopen.novel.dto.req;

import io.github.xxyopen.novel.core.common.req.PageReqDto;
import io.swagger.v3.oas.annotations.Parameter;
import lombok.Data;

/**
 * 我的上传 分页查询请求DTO
 *
 * @author xiongxiaoyang
 * @date 2026/10/21
 */
@Data
public class UploadBookReqDto extends PageReqDto {

    /**
     * 图书状态;0-连载中 1-已完结；不传查询全部
     */
    @Parameter(description = "图书状态;0-连载中 1-已完结；不传查询全部")
    private Integer bookStatus;

}
