package io.github.xxyopen.novel.dto.req;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

/**
 * 用户保存阅读进度 请求DTO
 *
 * @author xiongxiaoyang
 * @date 2026/10/21
 */
@Data
public class UserReadHistoryReqDto {

    @Schema(description = "小说ID", required = true)
    @NotNull(message = "小说ID不能为空！")
    private Long bookId;

    @Schema(description = "章节ID", required = true)
    @NotNull(message = "章节ID不能为空！")
    private Long chapterId;

}
