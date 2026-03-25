-- 电子书内容提取工具 - 数据库初始化脚本
-- PostgreSQL
-- 运行前请先创建数据库: CREATE DATABASE ebook_db;

-- ============================================
-- 1. 书籍表
-- ============================================
CREATE TABLE IF NOT EXISTS books (
    book_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    author VARCHAR(200),
    publisher VARCHAR(200),
    publish_date VARCHAR(50),
    isbn VARCHAR(30),
    file_path VARCHAR(1000) NOT NULL,
    file_type VARCHAR(10) NOT NULL,
    file_size BIGINT,
    cover_path VARCHAR(200),
    rating INTEGER DEFAULT 0,
    display_mode VARCHAR(30) DEFAULT 'original',
    extract_status VARCHAR(20) DEFAULT 'pending',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 2. 章节表
-- ============================================
CREATE TABLE IF NOT EXISTS chapters (
    chapter_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID NOT NULL REFERENCES books(book_id) ON DELETE CASCADE,
    chapter_name VARCHAR(500),
    chapter_order INT NOT NULL,
    chapter_level INT DEFAULT 0,
    parent_id UUID REFERENCES chapters(chapter_id)
);

-- ============================================
-- 3. 段落表（支持文本、表格和图片类型）
-- ============================================
CREATE TABLE IF NOT EXISTS paragraphs (
    para_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID NOT NULL REFERENCES chapters(chapter_id) ON DELETE CASCADE,
    content TEXT,
    para_order INT NOT NULL,
    para_type VARCHAR(20) DEFAULT 'text',
    style_info JSONB,
    is_footnote BOOLEAN DEFAULT FALSE,
    footnote_id VARCHAR(50)
);

-- ============================================
-- 4. 图片表
-- ============================================
CREATE TABLE IF NOT EXISTS images (
    image_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID NOT NULL REFERENCES chapters(chapter_id) ON DELETE CASCADE,
    image_path VARCHAR(1000) NOT NULL,
    image_order INT NOT NULL,
    width INT,
    height INT,
    alt VARCHAR(500),
    original_format VARCHAR(20)
);

-- ============================================
-- 5. 阅读历史表
-- ============================================
CREATE TABLE IF NOT EXISTS reading_history (
    id SERIAL PRIMARY KEY,
    book_id UUID NOT NULL REFERENCES books(book_id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL,
    chapter_name VARCHAR(500),
    book_title VARCHAR(500),
    read_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_duration INTEGER DEFAULT 0,
    progress INTEGER DEFAULT 0
);

-- ============================================
-- 6. 收藏表
-- ============================================
CREATE TABLE IF NOT EXISTS favorites (
    id SERIAL PRIMARY KEY,
    book_id UUID NOT NULL REFERENCES books(book_id) ON DELETE CASCADE,
    add_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 7. 阅读列表表（用户正在阅读的图书）
-- ============================================
CREATE TABLE IF NOT EXISTS reading_list (
    id SERIAL PRIMARY KEY,
    book_id UUID NOT NULL REFERENCES books(book_id) ON DELETE CASCADE,
    add_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 8. AI摘要表（AI辅助阅读功能）
-- ============================================
CREATE TABLE IF NOT EXISTS book_chapter_summary (
    summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID NOT NULL REFERENCES chapters(chapter_id) ON DELETE CASCADE,
    summary_content TEXT NOT NULL,
    model_name VARCHAR(100),
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_chapter_summary UNIQUE (chapter_id)
);

-- ============================================
-- 创建索引以提高查询性能
-- ============================================

-- 书籍表索引
CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);
CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
CREATE INDEX IF NOT EXISTS idx_books_status ON books(extract_status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_books_file_path_unique ON books(file_path) WHERE file_path IS NOT NULL;

-- 章节表索引
CREATE INDEX IF NOT EXISTS idx_chapters_book_id ON chapters(book_id);
CREATE INDEX IF NOT EXISTS idx_chapters_order ON chapters(chapter_order);
CREATE INDEX IF NOT EXISTS idx_chapters_parent_id ON chapters(parent_id);
CREATE INDEX IF NOT EXISTS idx_chapters_level ON chapters(chapter_level);

-- 段落表索引
CREATE INDEX IF NOT EXISTS idx_paragraphs_chapter_id ON paragraphs(chapter_id);
CREATE INDEX IF NOT EXISTS idx_paragraphs_order ON paragraphs(para_order);

-- 图片表索引
CREATE INDEX IF NOT EXISTS idx_images_chapter_id ON images(chapter_id);
CREATE INDEX IF NOT EXISTS idx_images_order ON images(image_order);

-- 阅读历史表索引
CREATE INDEX IF NOT EXISTS idx_reading_history_book_id ON reading_history(book_id);
CREATE INDEX IF NOT EXISTS idx_reading_history_read_time ON reading_history(read_time DESC);

-- AI摘要表索引
CREATE INDEX IF NOT EXISTS idx_chapter_summary_chapter_id ON book_chapter_summary(chapter_id);
CREATE INDEX IF NOT EXISTS idx_chapter_summary_create_time ON book_chapter_summary(create_time DESC);

-- ============================================
-- 8. 全文搜索支持（可选，用于提升搜索性能）
-- ============================================
-- 安装 pg_trgm 插件（需要超级用户权限）
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 为 paragraphs 表添加 trigram 索引（用于全文搜索加速）
CREATE INDEX IF NOT EXISTS idx_paragraphs_content_trgm ON paragraphs USING gin (content gin_trgm_ops);
-- 注意：如果搜索较慢，可以执行上面的语句创建索引
-- 注意：如果导入大量数据，建议先删除索引，导入完成后再重建索引
