package io.github.xxyopen.novel.dto.req;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 管理员修改书籍封面 请求DTO
 *
 * @author xiongxiaoyang
 * @date 2026/10/21
 */
@Data
public class AdminBookCoverReqDto {

    @Schema(description = "封面地址", required = true)
    @NotBlank(message = "封面地址不能为空")
    @Size(max = 100, message = "封面地址不能超过100个字符")
    private String picUrl;

}
