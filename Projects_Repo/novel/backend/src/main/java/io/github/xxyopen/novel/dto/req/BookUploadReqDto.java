package io.github.xxyopen.novel.dto.req;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;
import org.springframework.web.multipart.MultipartFile;

/**
 * 电子书上传 请求DTO
 *
 * @author xiongxiaoyang
 * @date 2022/5/17
 */
@Data
public class BookUploadReqDto {

    /**
     * 电子书文件
     */
    @Schema(description = "电子书文件", required = true)
    @NotNull
    private MultipartFile file;

    /**
     * 书名
     */
    @Schema(description = "书名", required = true)
    @NotBlank
    private String bookName;

    /**
     * 作者名
     */
    @Schema(description = "作者名")
    private String authorName;

    /**
     * 作品方向;0-男频 1-女频
     */
    @Schema(description = "作品方向;0-男频 1-女频", required = true)
    @NotNull
    private Integer workDirection;

    /**
     * 类别ID
     */
    @Schema(description = "类别ID", required = true)
    @NotNull
    private Long categoryId;

    /**
     * 类别名
     */
    @Schema(description = "类别名", required = true)
    @NotBlank
    private String categoryName;

    /**
     * 书籍描述
     */
    @Schema(description = "书籍描述")
    private String bookDesc;
}