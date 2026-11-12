package io.github.xxyopen.novel.dto.resp;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 电子书上传 响应DTO
 *
 * @author xiongxiaoyang
 * @date 2022/5/17
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class BookUploadRespDto {

    /**
     * 新上传图书的 ID
     */
    @Schema(description = "新上传图书的 ID")
    private Long bookId;

    /**
     * 书名
     */
    @Schema(description = "书名")
    private String bookName;

    /**
     * 解析出的章节数量
     */
    @Schema(description = "解析出的章节数量")
    private Integer chapterCount;

    /**
     * 总字数
     */
    @Schema(description = "总字数")
    private Integer wordCount;

    /**
     * 成功提示语
     */
    @Schema(description = "成功提示语")
    private String message;
}