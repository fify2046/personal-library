import fitz
import os
import logging
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from image_processor import clean_text, merge_paragraphs

logger = logging.getLogger(__name__)


@dataclass
class PDFChapter:
    name: str
    order: int
    paragraphs: List[str]
    images: List[Tuple[int, int, int]]
    image_order_counter: int = 0

    def add_paragraph(self, text: str):
        self.paragraphs.append(text)

    def add_image(self, xref: int, width: int, height: int):
        self.images.append((xref, width, height))
        self.image_order_counter += 1
        return self.image_order_counter


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

            chapters = self._extract_chapters(doc, progress_callback)

            doc.close()

            if not chapters:
                chapter = PDFChapter(name="正文", order=1, paragraphs=[], images=[])
                chapters = [chapter]

            return True, "PDF处理成功", {
                'chapters': len(chapters),
                'chapters_data': chapters
            }

        except Exception as e:
            logger.error(f"PDF提取失败: {file_path}, 错误: {e}")
            return False, str(e), {'chapters': 0, 'paragraphs': 0, 'images': 0}

    def _extract_chapters(self, doc, progress_callback=None) -> List[PDFChapter]:
        chapters = []
        current_chapter = None

        chapter_patterns = [
            r'^第[一二三四五六七八九十百千万\d]+[章卷].*',
            r'^[第 ][一二三四五六七八九十百千万\d]+[章卷].*',
            r'^(chapter|Chapter|CHAPTER)\s*[\divxlc]+',
            r'^(序章|前言|楔子|引子|尾声|后记|附录)',
            r'^[0-9]+\s*[\.\、]\s*[^\n]+',
        ]

        page_count = len(doc)
        image_count_per_page = {}

        for page_num in range(page_count):
            if progress_callback:
                progress_callback(page_num + 1, page_count)

            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                if block.get("type") == 0:
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
                                    order=len(chapters) + 1,
                                    paragraphs=[],
                                    images=[]
                                )
                            else:
                                if current_chapter is None:
                                    current_chapter = PDFChapter(
                                        name="前言",
                                        order=1,
                                        paragraphs=[],
                                        images=[]
                                    )

                                cleaned_text = clean_text(text)
                                if cleaned_text:
                                    current_chapter.add_paragraph(cleaned_text)

            images_on_page = self._extract_page_images(page, page_num)
            image_count_per_page[page_num] = images_on_page

        if current_chapter and current_chapter.paragraphs:
            chapters.append(current_chapter)

        for chapter in chapters:
            self._assign_images_to_chapter(chapter, image_count_per_page, doc)

        return chapters

    def _is_chapter_title(self, text: str, patterns: List[str]) -> bool:
        text = text.strip()
        if len(text) > 100:
            return False

        for pattern in patterns:
            if re.match(pattern, text):
                return True

        return False

    def _extract_page_images(self, page, page_num: int) -> List[Tuple[int, int, int, int]]:
        images = []
        try:
            image_list = page.get_images()
            for img_index, img in enumerate(image_list):
                xref = img[0]
                try:
                    base_image = page.parent.extract_image(xref)
                    width = base_image.get("width", 0)
                    height = base_image.get("height", 0)
                    images.append((xref, width, height, img_index))
                except Exception as e:
                    logger.warning(f"提取第{page_num}页图片{img_index}失败: {e}")
                    continue
        except Exception as e:
            logger.warning(f"提取第{page_num}页图片列表失败: {e}")

        return images

    def _assign_images_to_chapter(self, chapter: PDFChapter, image_count_per_page: Dict, doc):
        total_paragraphs_before = 0
        chapter_image_order = 1

        for page_num, images in image_count_per_page.items():
            for xref, width, height, img_index in images:
                result = self.image_processor.save_pdf_image(
                    xref, doc, "", "", chapter_image_order
                )
                if result:
                    chapter.add_image(xref, width, height)
                    chapter_image_order += 1
