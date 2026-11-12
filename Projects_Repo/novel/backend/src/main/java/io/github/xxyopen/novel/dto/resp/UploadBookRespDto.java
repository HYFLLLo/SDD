package io.github.xxyopen.novel.dto.resp;

import com.fasterxml.jackson.annotation.JsonFormat;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 我的上传 图书响应DTO
 *
 * @author xiongxiaoyang
 * @date 2026/10/21
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UploadBookRespDto {

    /**
     * 图书ID
     */
    @Schema(description = "图书ID")
    private Long id;

    /**
     * 作品方向；0-男频 1-女频
     */
    @Schema(description = "作品方向；0-男频 1-女频")
    private Integer workDirection;

    /**
     * 分类ID
     */
    @Schema(description = "分类ID")
    private Long categoryId;

    /**
     * 书名
     */
    @Schema(description = "书名")
    private String bookName;

    /**
     * 作者名
     */
    @Schema(description = "作者名")
    private String authorName;

    /**
     * 分类名
     */
    @Schema(description = "分类名")
    private String categoryName;

    /**
     * 书籍简介
     */
    @Schema(description = "书籍简介")
    private String bookDesc;

    /**
     * 封面地址
     */
    @Schema(description = "封面地址")
    private String picUrl;

    /**
     * 总字数
     */
    @Schema(description = "总字数")
    private Integer wordCount;

    /**
     * 章节数
     */
    @Schema(description = "章节数")
    private Integer chapterCount;

    /**
     * 图书状态;0-连载中 1-已完结
     */
    @Schema(description = "图书状态;0-连载中 1-已完结")
    private Integer bookStatus;

    /**
     * 最新章节名称
     */
    @Schema(description = "最新章节名称")
    private String lastChapterName;

    /**
     * 上传时间
     */
    @Schema(description = "上传时间")
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime createTime;

    /**
     * 更新时间
     */
    @Schema(description = "更新时间")
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime updateTime;

}
