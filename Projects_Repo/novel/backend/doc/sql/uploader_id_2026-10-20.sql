-- ============================================================
-- 迁移：book_info 新增 uploader_id 列 + idx_uploader_id 索引
-- 日期：2026-10-20
-- 目的：记录图书上传者（0 表示匿名上传），为「我的上传」管理功能提供归属字段。
--
-- 可重复执行（幂等）：先查 information_schema 判断列/索引是否已存在，
-- 不存在才执行 DDL。重复执行不会报错。
-- ============================================================

-- 1. 新增列 uploader_id
--    bigint unsigned NOT NULL DEFAULT 0：与 author_id 等 ID 列同类型；
--    DEFAULT 0 保证历史行可直接 ALTER 成功，无需回填。
SET @col_exists := (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'book_info'
      AND COLUMN_NAME = 'uploader_id'
);

SET @ddl_add_column := IF(
    @col_exists = 0,
    'ALTER TABLE book_info ADD COLUMN uploader_id bigint unsigned NOT NULL DEFAULT 0 COMMENT ''上传者用户ID;0-匿名''',
    'SELECT ''column uploader_id already exists'' AS info'
);

PREPARE stmt FROM @ddl_add_column;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. 新增索引 idx_uploader_id
SET @idx_exists := (
    SELECT COUNT(*)
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'book_info'
      AND INDEX_NAME = 'idx_uploader_id'
);

SET @ddl_add_index := IF(
    @idx_exists = 0,
    'ALTER TABLE book_info ADD KEY idx_uploader_id (uploader_id)',
    'SELECT ''index idx_uploader_id already exists'' AS info'
);

PREPARE stmt FROM @ddl_add_index;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
