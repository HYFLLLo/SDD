package io.github.xxyopen.novel.dto.req;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 管理员修改书籍基础信息 请求DTO
 *
 * @author xiongxiaoyang
 * @date 2026/10/21
 */
@Data
public class AdminBookUpdateReqDto {

    @Schema(description = "书名", required = true)
    @NotBlank(message = "书名不能为空")
    @Size(max = 50, message = "书名不能超过50个字符")
    private String bookName;

    @Schema(description = "作者名", required = true)
    @NotBlank(message = "作者名不能为空")
    @Size(max = 50, message = "作者名不能超过50个字符")
    private String authorName;

    @Schema(description = "作品方向；0-男频 1-女频", required = true)
    @NotNull(message = "作品方向不能为空")
    @Min(0)
    @Max(1)
    private Integer workDirection;

    @Schema(description = "分类ID", required = true)
    @NotNull(message = "分类ID不能为空")
    private Long categoryId;

    @Schema(description = "分类名", required = true)
    @NotBlank(message = "分类名不能为空")
    @Size(max = 50, message = "分类名不能超过50个字符")
    private String categoryName;

    @Schema(description = "书籍简介")
    @Size(max = 2000, message = "书籍简介不能超过2000个字符")
    private String bookDesc;

    @Schema(description = "图书状态；0-连载中 1-已完结", required = true)
    @NotNull(message = "图书状态不能为空")
    @Min(0)
    @Max(1)
    private Integer bookStatus;

}
