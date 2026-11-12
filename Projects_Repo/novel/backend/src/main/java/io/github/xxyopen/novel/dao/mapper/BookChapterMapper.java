package io.github.xxyopen.novel.dao.mapper;

import io.github.xxyopen.novel.dao.entity.BookChapter;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import io.github.xxyopen.novel.dto.resp.BookChapterCountDto;
import java.util.List;
import org.apache.ibatis.annotations.Param;

/**
 * <p>
 * 小说章节 Mapper 接口
 * </p>
 *
 * @author xiongxiaoyang
 * @date 2022/05/11
 */
public interface BookChapterMapper extends BaseMapper<BookChapter> {

    /**
     * 批量统计指定图书的章节数量（单次 GROUP BY，避免逐本查询）
     *
     * @param bookIds 图书ID集合
     * @return 图书ID与章节数量列表
     */
    List<BookChapterCountDto> countChaptersByBookIds(@Param("bookIds") List<Long> bookIds);

}
