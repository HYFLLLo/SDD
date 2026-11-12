package io.github.xxyopen.novel.dto.resp;

import lombok.Data;

/**
 * 小说章节数量统计DTO
 *
 * @author xiongxiaoyang
 * @date 2026/10/21
 */
@Data
public class BookChapterCountDto {

    /**
     * 小说ID
     */
    private Long bookId;

    /**
     * 章节数量
     */
    private Long chapterCount;

}
