package io.github.xxyopen.novel.dto.req;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

/**
 * 我的上传 切换图书状态请求DTO
 *
 * @author xiongxiaoyang
 * @date 2026/10/21
 */
@Data
public class UploadBookStatusReqDto {

    /**
     * 目标状态;0-连载中 1-已完结
     */
    @Schema(description = "目标状态;0-连载中 1-已完结", required = true)
    @NotNull
    @Min(0)
    @Max(1)
    private Integer bookStatus;

}
