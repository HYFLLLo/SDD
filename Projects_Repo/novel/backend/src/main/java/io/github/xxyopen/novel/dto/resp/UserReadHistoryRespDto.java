package io.github.xxyopen.novel.dto.resp;

import com.fasterxml.jackson.annotation.JsonFormat;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;
import lombok.Builder;
import lombok.Data;

/**
 * 用户阅读历史 响应DTO
 *
 * @author xiongxiaoyang
 * @date 2026/10/21
 */
@Data
@Builder
public class UserReadHistoryRespDto {

    @Schema(description = "小说ID")
    private Long bookId;

    @Schema(description = "小说名")
    private String bookName;

    @Schema(description = "小说封面")
    private String picUrl;

    @Schema(description = "作者名")
    private String authorName;

    @Schema(description = "上次阅读章节ID")
    private Long chapterId;

    @Schema(description = "上次阅读章节名")
    private String chapterName;

    @Schema(description = "阅读时间")
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm")
    private LocalDateTime updateTime;

}
