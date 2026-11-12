package io.github.xxyopen.novel.dto.req;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.Data;
import org.springframework.web.multipart.MultipartFile;

/**
 * 管理员替换书籍内容 请求DTO
 *
 * @author xiongxiaoyang
 * @date 2026/10/21
 */
@Data
public class AdminBookContentReqDto {

    @Schema(description = "电子书文件，仅支持 .txt / .epub", required = true)
    @NotNull(message = "电子书文件不能为空")
    private MultipartFile file;

}
