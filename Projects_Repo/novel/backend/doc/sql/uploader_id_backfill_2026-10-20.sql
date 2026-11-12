-- ============================================================
-- 迁移：回填历史上传书「仙逆」「丹道宗师」的 uploader_id
-- 日期：2026-10-20（2026-10-21 补充「丹道宗师」）
-- 目的：将匿名历史上传书归属到管理员 admin 名下。
--       幂等：第二次执行时 uploader_id = 0 的条件不再满足，影响 0 行。
-- ============================================================

UPDATE book_info b
JOIN user_info u ON u.username = 'admin'
SET b.uploader_id = u.id,
    b.update_time = NOW()
WHERE b.book_name IN ('仙逆', '丹道宗师')
  AND b.author_id = 0
  AND b.uploader_id = 0;
