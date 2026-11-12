package io.github.xxyopen.novel.dto.req;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 我的上传 修改图书作者名请求DTO
 *
 * @author xiongxiaoyang
 * @date 2026/10/21
 */
@Data
public class UploadBookAuthorReqDto {

    /**
     * 作者名
     */
    @Schema(description = "作者名", required = true)
    @NotBlank(message = "作者名不能为空！")
    @Size(max = 50, message = "作者名不能超过50个字符！")
    private String authorName;

}