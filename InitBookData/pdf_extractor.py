import fitz
import os
import logging
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from image_processor import clean_text, merge_paragraphs

logger = logging.getLogger(__name__)


@dataclass
class PDFChapter:
    name: str
    order: int
    paragraphs: List[Dict] = field(default_factory=list)
    images: List[Dict] = field(default_factory=list)

    def add_paragraph(self, text: str, para_type: str = 'text'):
        self.paragraphs.append({
            'type': para_type,
            'content': text
        })

    def add_image(self, path: str, width: int, height: int, order: int, original_format: str = ''):
        self.images.append({
            'path': path,
            'width': width,
            'height': height,
            'order': order,
            'original_format': original_format
        })


class PDFExtractor:
    def __init__(self, image_processor):
        self.image_processor = image_processor

    def is_scanned_pdf(self, doc) -> bool:
        try:
            for page_num in range(min(5, len(doc))):
                page = doc[page_num]
                text = page.get_text()
                if text and len(text.strip()) > 50:
                    return False
            return True
        except Exception as e:
            logger.error(f"检查PDF类型失败: {e}")
            return True

    def extract(self, file_path: str, book_id: str, progress_callback=None) -> Tuple[bool, str, Dict]:
        try:
            doc = fitz.open(file_path)
            logger.info(f"PDF文件打开成功: {file_path}, 页数: {len(doc)}")

            if self.is_scanned_pdf(doc):
                doc.close()
                logger.warning(f"跳过扫描版PDF: {file_path}")
                return False, "扫描版PDF，跳过处理", {'chapters': 0, 'paragraphs': 0, 'images': 0}

            # 提取封面（第一页的第一个图片）
            cover_path = self._extract_cover(doc, book_id)

            # 提取章节和图片
            chapters, extracted_images = self._extract_chapters_and_images(doc, book_id, progress_callback)

            doc.close()

            if not chapters:
                chapter = PDFChapter(name="正文", order=1)
                chapters = [chapter]

            return True, "PDF处理成功", {
                'chapters': len(chapters),
                'chapters_data': chapters,
                'cover_path': cover_path,
                'extracted_images': extracted_images
            }

        except Exception as e:
            logger.error(f"PDF提取失败: {file_path}, 错误: {e}")
            return False, str(e), {'chapters': 0, 'paragraphs': 0, 'images': 0}

    def _extract_cover(self, doc, book_id: str) -> Optional[str]:
        """提取PDF封面（第一页的第一个图片）"""
        try:
            if len(doc) == 0:
                return None

            # 获取第一页
            first_page = doc[0]
            image_list = first_page.get_images()

            if not image_list:
                return None

            # 取第一个图片作为封面
            xref = image_list[0][0]
            cover_path = self.image_processor.save_cover_image(xref, doc, book_id)

            return cover_path

        except Exception as e:
            logger.warning(f"提取PDF封面失败: {e}")
            return None

    def _extract_chapters_and_images(self, doc, book_id: str, progress_callback=None) -> Tuple[List[PDFChapter], List[Dict]]:
        """提取章节和图片，返回章节列表和提取的图片信息列表"""
        chapters = []
        current_chapter = None
        extracted_images = []
        global_image_order = 1

        chapter_patterns = [
            r'^第[一二三四五六七八九十百千万\d]+[章卷].*',
            r'^[第 ][一二三四五六七八九十百千万\d]+[章卷].*',
            r'^(chapter|Chapter|CHAPTER)\s*[\divxlc]+',
            r'^(序章|前言|楔子|引子|尾声|后记|附录)',
            r'^[0-9]+\s*[\.\、]\s*[^\n]+',
        ]

        page_count = len(doc)

        for page_num in range(page_count):
            if progress_callback:
                progress_callback(page_num + 1, page_count)

            page = doc[page_num]

            # 先提取当前页面的图片
            page_images = self._extract_and_save_page_images(page, page_num, book_id, global_image_order)
            if page_images:
                extracted_images.extend(page_images)
                global_image_order += len(page_images)

            # 提取文本内容
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                if block.get("type") == 0:  # 文本块
                    for line in block.get("lines", []):
                        text_parts = []
                        for span in line.get("spans", []):
                            text = span.get("text", "")
                            text_parts.append(text)

                        if text_parts:
                            text = "".join(text_parts).strip()

                            if not text:
                                continue

                            is_chapter_title = self._is_chapter_title(text, chapter_patterns)

                            if is_chapter_title:
                                if current_chapter and current_chapter.paragraphs:
                                    chapters.append(current_chapter)

                                current_chapter = PDFChapter(
                                    name=text[:100],
                                    order=len(chapters) + 1
                                )
                            else:
                                if current_chapter is None:
                                    current_chapter = PDFChapter(
                                        name="前言",
                                        order=1
                                    )

                                cleaned_text = clean_text(text)
                                if cleaned_text:
                                    current_chapter.add_paragraph(cleaned_text)

            # 将当前页面的图片添加到当前章节
            if current_chapter and page_images:
                for img_info in page_images:
                    current_chapter.add_image(
                        path=img_info['path'],
                        width=img_info['width'],
                        height=img_info['height'],
                        order=img_info['order'],
                        original_format=img_info.get('original_format', '')
                    )
                    # 同时添加图片段落
                    current_chapter.add_paragraph(img_info['path'], para_type='image')

        if current_chapter and current_chapter.paragraphs:
            chapters.append(current_chapter)

        return chapters, extracted_images

    def _extract_and_save_page_images(self, page, page_num: int, book_id: str, start_order: int) -> List[Dict]:
        """提取并保存页面中的图片，返回图片信息列表"""
        images = []
        try:
            image_list = page.get_images()
            for img_index, img in enumerate(image_list):
                xref = img[0]
                try:
                    # 使用 chapter_1 作为默认章节目录
                    result = self.image_processor.save_pdf_image(
                        xref, page.parent, book_id, "chapter_1", start_order + img_index
                    )
                    if result:
                        path, width, height, ext = result
                        images.append({
                            'path': path,
                            'width': width,
                            'height': height,
                            'order': start_order + img_index,
                            'original_format': ext,
                            'chapter_order': 1,  # PDF 默认只有一个章节
                            'page_num': page_num
                        })
                except Exception as e:
                    logger.warning(f"提取第{page_num}页图片{img_index}失败: {e}")
                    continue
        except Exception as e:
            logger.warning(f"提取第{page_num}页图片列表失败: {e}")

        return images

    def _is_chapter_title(self, text: str, patterns: List[str]) -> bool:
        text = text.strip()
        if len(text) > 100:
            return False

        for pattern in patterns:
            if re.match(pattern, text):
                return True

        return False
