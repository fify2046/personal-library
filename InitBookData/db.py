import psycopg2
from psycopg2 import pool
import uuid
import os
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    _instance = None
    _pool = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, host='localhost', port=5432, database='ebook_db',
                 user='postgres', password='postgres'):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password

    def init_pool(self, min_connections=1, max_connections=10):
        try:
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                min_connections,
                max_connections,
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            logger.info("数据库连接池初始化成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接池初始化失败: {e}")
            return False

    def close_pool(self):
        if self._pool:
            self._pool.closeall()
            logger.info("数据库连接池已关闭")

    @contextmanager
    def get_connection(self):
        conn = None
        try:
            if self._pool is None:
                self.init_pool()
            conn = self._pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            if conn and self._pool:
                self._pool.putconn(conn)

    def check_connection(self) -> bool:
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False

    def insert_book(self, title: str, file_path: str, file_type: str,
                    file_size: int, author: str = None) -> Optional[str]:
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO books (title, author, file_path, file_type, file_size, extract_status)
                        VALUES (%s, %s, %s, %s, %s, 'pending')
                        RETURNING book_id
                    """, (title, author, file_path, file_type, file_size))
                    book_id = cur.fetchone()[0]
                    logger.info(f"书籍插入成功: {title}, book_id: {book_id}")
                    return str(book_id)
        except Exception as e:
            logger.error(f"插入书籍失败: {e}")
            return None

    def book_exists(self, file_path: str) -> bool:
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM books WHERE file_path = %s", (file_path,))
                    return cur.fetchone() is not None
        except Exception as e:
            logger.error(f"检查书籍是否存在失败: {e}")
            return False

    def book_exists_by_title(self, title: str) -> bool:
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM books WHERE title = %s", (title,))
                    return cur.fetchone() is not None
        except Exception as e:
            logger.error(f"检查书名是否存在失败: {e}")
            return False

    def update_book_status(self, book_id: str, status: str):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE books SET extract_status = %s, create_time = create_time
                        WHERE book_id = %s
                    """, (status, book_id))
                    logger.info(f"书籍状态更新: {book_id} -> {status}")
        except Exception as e:
            logger.error(f"更新书籍状态失败: {e}")

    def update_book_cover(self, book_id: str, cover_path: str, author: str = None):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    if author:
                        cur.execute("""
                            UPDATE books SET cover_path = %s, author = %s, create_time = create_time
                            WHERE book_id = %s
                        """, (cover_path, author, book_id))
                    else:
                        cur.execute("""
                            UPDATE books SET cover_path = %s, create_time = create_time
                            WHERE book_id = %s
                        """, (cover_path, book_id))
                    logger.info(f"书籍封面更新: {book_id} -> {cover_path}")
        except Exception as e:
            logger.error(f"更新书籍封面失败: {e}")

    def get_book_id_by_path(self, file_path: str) -> Optional[str]:
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT book_id FROM books WHERE file_path = %s", (file_path,))
                    result = cur.fetchone()
                    return str(result[0]) if result else None
        except Exception as e:
            logger.error(f"获取书籍ID失败: {e}")
            return None

    def insert_chapter(self, book_id: str, chapter_name: str, chapter_order: int, 
                       chapter_level: int = 0, parent_id: str = None) -> Optional[str]:
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO chapters (book_id, chapter_name, chapter_order, chapter_level, parent_id)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING chapter_id
                    """, (book_id, chapter_name, chapter_order, chapter_level, parent_id))
                    chapter_id = cur.fetchone()[0]
                    return str(chapter_id)
        except Exception as e:
            logger.error(f"插入章节失败: {e}")
            return None

    def insert_chapters_with_hierarchy(self, chapters: List[Dict]) -> Dict[str, str]:
        if not chapters:
            return {}
        
        href_to_id = {}
        temp_id_to_real_id = {}
        
        sorted_chapters = sorted(chapters, key=lambda x: (x.get('level', 0), x.get('order', 0)))
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    for chapter in sorted_chapters:
                        parent_id = None
                        parent_temp_id = chapter.get('parent_id')
                        if parent_temp_id and parent_temp_id in temp_id_to_real_id:
                            parent_id = temp_id_to_real_id[parent_temp_id]
                        
                        cur.execute("""
                            INSERT INTO chapters (book_id, chapter_name, chapter_order, chapter_level, parent_id)
                            VALUES (%s, %s, %s, %s, %s)
                            RETURNING chapter_id
                        """, (chapter['book_id'], chapter['name'], chapter['order'], 
                              chapter.get('level', 0), parent_id))
                        chapter_id = str(cur.fetchone()[0])
                        
                        temp_id = chapter.get('temp_id')
                        if temp_id:
                            temp_id_to_real_id[temp_id] = chapter_id
                        
                        href = chapter.get('href', '')
                        if href:
                            href_to_id[href] = chapter_id
                        
                        chapter['chapter_id'] = chapter_id
                    
                    logger.info(f"批量插入章节: {len(chapters)} 条")
                    return href_to_id
        except Exception as e:
            logger.error(f"批量插入章节失败: {e}")
            return {}

    def insert_chapters_batch(self, chapters: List[Tuple[str, str, int]]) -> int:
        if not chapters:
            return 0
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.executemany("""
                        INSERT INTO chapters (book_id, chapter_name, chapter_order)
                        VALUES (%s, %s, %s)
                        RETURNING chapter_id
                    """, chapters)
                    inserted = cur.rowcount
                    return inserted
        except Exception as e:
            logger.error(f"批量插入章节失败: {e}")
            return 0

    def insert_paragraphs_batch(self, paragraphs: List[Tuple[str, str, int, str]]) -> int:
        if not paragraphs:
            return 0
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.executemany("""
                        INSERT INTO paragraphs (chapter_id, content, para_order, para_type)
                        VALUES (%s, %s, %s, %s)
                    """, paragraphs)
                    inserted = cur.rowcount
                    logger.info(f"批量插入段落: {inserted} 条")
                    return inserted
        except Exception as e:
            logger.error(f"批量插入段落失败: {e}")
            return 0

    def insert_paragraphs_batch_with_footnote(self, paragraphs: List[Tuple[str, str, int, str, bool]]) -> int:
        if not paragraphs:
            return 0
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    for para in paragraphs:
                        chapter_id, content, para_order, para_type, is_footnote = para
                        cur.execute("""
                            INSERT INTO paragraphs (chapter_id, content, para_order, para_type, is_footnote)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (chapter_id, content, para_order, para_type, is_footnote))
                    inserted = len(paragraphs)
                    logger.info(f"批量插入段落: {inserted} 条")
                    return inserted
        except Exception as e:
            logger.error(f"批量插入段落失败: {e}")
            return 0

    def insert_images_batch(self, images: List[Tuple[str, str, int, int, int, str, str]]) -> int:
        if not images:
            return 0
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.executemany("""
                        INSERT INTO images (chapter_id, image_path, image_order, width, height, alt, original_format)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, images)
                    inserted = cur.rowcount
                    logger.info(f"批量插入图片: {inserted} 条")
                    return inserted
        except Exception as e:
            logger.error(f"批量插入图片失败: {e}")
            return 0

    def get_all_books(self) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT book_id, title, author, file_path, file_type, 
                               file_size, create_time, extract_status
                        FROM books ORDER BY create_time DESC
                    """)
                    columns = [desc[0] for desc in cur.description]
                    return [dict(zip(columns, row)) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"获取所有书籍失败: {e}")
            return []

    def delete_book(self, book_id: str) -> bool:
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM books WHERE book_id = %s", (book_id,))
                    logger.info(f"删除书籍: {book_id}")
                    return True
        except Exception as e:
            logger.error(f"删除书籍失败: {e}")
            return False


_db_manager = None


def get_db_manager(host='localhost', port=5432, database='ebook_db',
                   user='postgres', password='postgres') -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(host, port, database, user, password)
    return _db_manager
