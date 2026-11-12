package io.github.xxyopen.novel.dto.req;

import io.github.xxyopen.novel.core.common.req.PageReqDto;
import io.swagger.v3.oas.annotations.Parameter;
import lombok.Data;

/**
 * 管理员书籍管理 分页查询请求DTO
 *
 * @author xiongxiaoyang
 * @date 2026/10/21
 */
@Data
public class AdminBookReqDto extends PageReqDto {

    /**
     * 书名关键字，模糊查询
     */
    @Parameter(description = "书名关键字")
    private String bookName;

    /**
     * 图书状态；0-连载中 1-已完结；不传查询全部
     */
    @Parameter(description = "图书状态；0-连载中 1-已完结；不传查询全部")
    private Integer bookStatus;

}
