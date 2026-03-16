import os
import logging
import uuid
import re
import json
import zipfile
import copy
import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from ebooklib import epub
from bs4 import BeautifulSoup, NavigableString
from concurrent.futures import ThreadPoolExecutor, as_completed
from image_processor import clean_text

logger = logging.getLogger(__name__)

# 线程池配置（可通过UI修改）
CHAPTER_EXTRACTION_WORKERS = 8  # 章节内容提取线程数，默认8
IMAGE_SAVE_WORKERS = 4  # 图片保存线程数，默认4

@dataclass
class EPUBChapter:
    name: str
    order: int
    level: int = 0
    parent_id: str = None
    href: str = ""
    paragraphs: List[Dict] = field(default_factory=list)
    image_refs: List[Dict] = field(default_factory=list)
    html_content: str = ""


class EPUBExtractor:
    def __init__(self, image_processor, chapter_workers=None, image_workers=None):
        self.image_processor = image_processor
        self.ncx_ns = {'ncx': 'http://www.daisy.org/z3986/2005/ncx/'}
        # 使用传入的线程数或默认值
        self.chapter_workers = chapter_workers if chapter_workers else CHAPTER_EXTRACTION_WORKERS
        self.image_workers = image_workers if image_workers else IMAGE_SAVE_WORKERS

    def extract(self, file_path: str, book_id: str, progress_callback=None) -> Tuple[bool, str, Dict]:
        try:
            book = epub.read_epub(file_path, {'ignore_ncx': False})
            logger.debug(f"EPUB文件打开成功: {file_path}")

            title = self._get_metadata(book, 'title') or os.path.splitext(os.path.basename(file_path))[0]
            author = self._get_metadata(book, 'creator') or "未知作者"

            toc_hierarchy = self._parse_ncx_hierarchy(file_path)
            
            if not toc_hierarchy:
                logger.warning("NCX解析失败，使用默认目录提取")
                toc_hierarchy = self._build_toc_from_spine(book)

            chapters = self._extract_chapters_with_hierarchy(book, toc_hierarchy, progress_callback)

            if not chapters:
                chapter = EPUBChapter(name="正文", order=1, paragraphs=[], image_refs=[])
                chapters = [chapter]

            extracted_images = self.extract_images_from_epub(book, chapters, book_id, file_path)
            
            cover_path = self.extract_cover(book, book_id, file_path)

            return True, "EPUB处理成功", {
                'title': title,
                'author': author,
                'chapters': len(chapters),
                'chapters_data': chapters,
                'book': book,
                'extracted_images': extracted_images,
                'cover_path': cover_path
            }

        except Exception as e:
            logger.error(f"EPUB提取失败: {file_path}, 错误: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e), {'chapters': 0, 'paragraphs': 0, 'images': 0}

    def _get_metadata(self, book, key: str) -> Optional[str]:
        try:
            if key in book.metadata:
                values = book.metadata[key]
                if values:
                    for item in values:
                        if item[0]:
                            return item[0]
            return None
        except Exception as e:
            logger.warning(f"获取元数据{key}失败: {e}")
            return None

    def _parse_ncx_hierarchy(self, file_path: str) -> List[Dict]:
        """解析NCX文件或EPUB3导航文档获取层级目录"""
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                ncx_files = [f for f in zf.namelist() if f.endswith('.ncx')]

                if ncx_files:
                    ncx_content = zf.read(ncx_files[0])
                    return self._parse_ncx_content(ncx_content)

                nav_files = [f for f in zf.namelist() if 'nav' in f.lower() and (f.endswith('.xhtml') or f.endswith('.html'))]
                if nav_files:
                    for nav_file in nav_files:
                        nav_content = zf.read(nav_file)
                        toc = self._parse_epub3_nav(nav_content)
                        if toc:
                            logger.debug(f"从EPUB3导航文档解析到 {len(toc)} 个目录项")
                            return toc

                logger.warning("未找到NCX文件或EPUB3导航文档")
                return []

        except Exception as e:
            logger.error(f"解析目录失败: {e}")
            return []

    def _parse_epub3_nav(self, nav_content: bytes) -> List[Dict]:
        """解析EPUB3 navigation.xhtml文档"""
        try:
            soup = BeautifulSoup(nav_content, 'html.parser')

            navs = soup.find_all('nav', {'epub:type': 'toc'})
            if not navs:
                navs = soup.find_all('nav')

            if not navs:
                return []

            toc = []
            order = [0]

            def parse_list_items(li_element, level=0, parent_href=""):
                if not li_element:
                    return

                a_tag = li_element.find('a', href=True)
                if a_tag:
                    href = a_tag.get('href', '')
                    title = a_tag.get_text(strip=True)

                    order[0] += 1
                    toc.append({
                        'title': title,
                        'href': href,
                        'level': level,
                        'order': order[0],
                        'parent_href': parent_href
                    })

                ol_tag = li_element.find('ol')
                if ol_tag:
                    for child_li in ol_tag.find_all('li', recursive=False):
                        current_href = href if a_tag else parent_href
                        parse_list_items(child_li, level + 1, current_href)

            for nav in navs:
                ol = nav.find('ol')
                if ol:
                    for li in ol.find_all('li', recursive=False):
                        parse_list_items(li, 0, "")

            return toc

        except Exception as e:
            logger.debug(f"解析EPUB3导航失败: {e}")
            return []

    def _parse_ncx_content(self, ncx_content: bytes) -> List[Dict]:
        """解析NCX XML内容"""
        try:
            root = ET.fromstring(ncx_content)
            nav_map = root.find('ncx:navMap', self.ncx_ns)
            
            if nav_map is None:
                return []
            
            toc = []
            order = [0]
            
            def parse_nav_point(nav_point, level=0, parent_href=""):
                text_elem = nav_point.find('ncx:navLabel/ncx:text', self.ncx_ns)
                content_elem = nav_point.find('ncx:content', self.ncx_ns)

                title = text_elem.text if text_elem is not None else ""
                src_full = content_elem.get('src', '') if content_elem is not None else ""
                src_base = src_full.split('#')[0]

                order[0] += 1
                entry = {
                    'title': title,
                    'href': src_full,
                    'level': level,
                    'order': order[0],
                    'parent_href': parent_href
                }
                toc.append(entry)

                for child in nav_point.findall('ncx:navPoint', self.ncx_ns):
                    parse_nav_point(child, level + 1, src_base)
            
            for nav_point in nav_map.findall('ncx:navPoint', self.ncx_ns):
                parse_nav_point(nav_point, 0, "")
            
            logger.debug(f"NCX解析完成，共 {len(toc)} 个目录项")
            return toc
            
        except Exception as e:
            logger.error(f"解析NCX内容失败: {e}")
            return []

    def _build_toc_from_spine(self, book) -> List[Dict]:
        """从spine构建目录（备用方案）"""
        toc = []
        for idx, item in enumerate(book.spine):
            if isinstance(item, tuple):
                item_id = item[0]
            else:
                item_id = str(item)
            
            for book_item in book.get_items():
                if book_item.get_type() == 9:
                    if item_id in book_item.get_name() or book_item.get_name().endswith(item_id):
                        soup = BeautifulSoup(book_item.get_content(), 'html.parser')
                        chapter_name = self._extract_chapter_name_from_soup(soup)
                        toc.append({
                            'title': chapter_name,
                            'href': book_item.get_name(),
                            'level': 0,
                            'order': idx + 1,
                            'parent_href': ''
                        })
                        break
        return toc

    def _extract_chapter_name_from_soup(self, soup) -> str:
        """从HTML中提取章节名称"""
        h_tags = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        for h in h_tags:
            text = h.get_text().strip()
            if text and len(text) < 100:
                return text
        
        title_tag = soup.find('title')
        if title_tag:
            text = title_tag.get_text().strip()
            if text:
                return text
        
        return "未命名章节"

    def _extract_chapters_with_hierarchy(self, book, toc_hierarchy: List[Dict], progress_callback=None) -> List[EPUBChapter]:
        """根据层级目录提取章节内容"""
        chapters = []
        href_to_temp_id = {}
        self.current_book = book

        items_by_name = {}
        for item in book.get_items():
            if item.get_type() == 9:
                name = item.get_name()
                items_by_name[name] = item
                basename = os.path.basename(name)
                items_by_name[basename] = item
        
        toc_hrefs = set()
        for toc_entry in toc_hierarchy:
            href = toc_entry['href']
            href_base = href.split('#')[0]
            toc_hrefs.add(href_base)
        
        logger.debug(f"目录href数量: {len(toc_hrefs)}")
        
        if not toc_hierarchy:
            logger.warning("目录为空，使用spine构建")
            toc_hierarchy = self._build_toc_from_spine(book)
        
        toc_hrefs = {item['href'].split('#')[0] for item in toc_hierarchy if 'href' in item}
        logger.debug(f"目录href数量: {len(toc_hrefs)}")
        
        # 构建 id -> item 映射
        items_by_id = {}
        for item in book.get_items():
            if item.get_type() == 9:
                items_by_id[item.get_id()] = item
        
        spine_pre_items = []
        try:
            if book.spine:
                logger.debug(f"Spine项目数量: {len(book.spine)}")
                for spine_idx, spine_item in enumerate(book.spine):
                    if isinstance(spine_item, tuple):
                        item_id = spine_item[0]
                    else:
                        item_id = str(spine_item)
                    
                    logger.debug(f"处理Spine项目 {spine_idx}: item_id={item_id}")
                    
                    # 首先通过 id 查找
                    spine_content_item = items_by_id.get(item_id)
                    if spine_content_item:
                        spine_href = spine_content_item.get_name()
                        logger.debug(f"  通过id匹配到item: {spine_href}")
                    else:
                        # 回退到 name 匹配
                        spine_href = None
                        spine_content_item = None
                        for item in book.get_items():
                            if item.get_type() == 9:
                                item_name = item.get_name()
                                if item_id in item_name or item_name.endswith(item_id) or item_name == item_id:
                                    spine_href = item_name
                                    spine_content_item = item
                                    logger.debug(f"  通过name匹配到item: {item_name}")
                                    break
                                basename = os.path.basename(item_name)
                                if basename == item_id:
                                    spine_href = item_name
                                    spine_content_item = item
                                    logger.debug(f"  通过basename匹配到item: {item_name}")
                                    break
                    
                    if not spine_content_item:
                        logger.warning(f"  未找到spine项目 {spine_idx} ({item_id}) 对应的内容项")
                        continue
                    
                    spine_href = spine_content_item.get_name()
                    spine_basename = os.path.basename(spine_href)
                    in_toc = False
                    matched_toc_href = None
                    for toc_href in toc_hrefs:
                        toc_basename = os.path.basename(toc_href)
                        if (spine_href == toc_href or 
                            spine_basename == toc_basename or
                            spine_href.endswith(toc_href) or toc_href.endswith(spine_href)):
                            in_toc = True
                            matched_toc_href = toc_href
                            break
                    
                    if in_toc:
                        logger.debug(f"Spine项目 {spine_idx} ({spine_href}) 在目录中匹配到 {matched_toc_href}，停止添加前置页面")
                        break
                    else:
                        logger.debug(f"Spine项目 {spine_idx} ({spine_href}) 不在目录中，将作为前置页面添加")
                        spine_pre_items.append((spine_idx, spine_href, spine_content_item))
        except Exception as e:
            logger.warning(f"处理spine前置项目失败: {e}")
            logger.exception("详细错误")
        
        processed_hrefs = set()
        
        pre_order = 0
        for spine_idx, spine_href, spine_item in spine_pre_items:
            if spine_item:
                pre_order += 1
                soup = BeautifulSoup(spine_item.get_content(), 'html.parser')
                content_result = self._extract_content_with_images(soup, pre_order)
                
                temp_id = str(uuid.uuid4())
                chapter_name = "封面" if pre_order == 1 else f"前言{pre_order - 1}" if pre_order > 1 else "前置页面"
                chapter = EPUBChapter(
                    name=chapter_name,
                    order=pre_order,
                    level=0,
                    parent_id=None,
                    href=spine_href,
                    paragraphs=content_result['paragraphs'],
                    image_refs=content_result['image_refs'],
                    html_content=str(soup)
                )
                chapter.temp_id = temp_id
                chapters.append(chapter)
                href_to_temp_id[spine_href] = temp_id
                processed_hrefs.add(spine_href)
                logger.debug(f"添加前置章节: {chapter_name}, href={spine_href}")
        
        order_offset = pre_order

        # 按 href_base 分组 toc_entry，同一 HTML 文件可能有多个目录项
        href_to_toc_entries = {}
        for toc_entry in toc_hierarchy:
            href = toc_entry['href']
            href_base = href.split('#')[0]
            if href_base not in href_to_toc_entries:
                href_to_toc_entries[href_base] = []
            href_to_toc_entries[href_base].append(toc_entry)

        # 收集所有需要处理的章节任务
        chapter_tasks = []
        for href_base, toc_entries in href_to_toc_entries.items():
            # 检查是否已处理
            if href_base in processed_hrefs:
                continue

            item = items_by_name.get(href_base)

            if not item:
                for name, it in items_by_name.items():
                    if name.endswith(href_base) or href_base.endswith(name):
                        item = it
                        break

            if not item:
                logger.warning(f"找不到章节内容: {href_base}")
                continue

            # 同一 HTML 文件有多个目录项，需要拆分
            if len(toc_entries) > 1:
                logger.debug(f"同一 HTML 文件有 {len(toc_entries)} 个目录项: {href_base}")
                # 检查是否有锚点来区分不同章节
                has_anchors = any('#' in entry['href'] for entry in toc_entries)

                if has_anchors:
                    # 有锚点，为每个目录项创建任务
                    for i, toc_entry in enumerate(toc_entries):
                        new_order = toc_entry['order'] + order_offset + i * 0.1
                        chapter_tasks.append({
                            'toc_entry': toc_entry,
                            'item': item,
                            'href_base': href_base,
                            'new_order': new_order,
                            'idx': len(chapter_tasks)
                        })
                else:
                    # 没有锚点，只保留第一个目录项，避免重复内容
                    logger.debug(f"目录项无锚点，只保留第一个: {toc_entries[0]['title']}")
                    processed_hrefs.add(href_base)
                    toc_entry = toc_entries[0]
                    new_order = toc_entry['order'] + order_offset
                    chapter_tasks.append({
                        'toc_entry': toc_entry,
                        'item': item,
                        'href_base': href_base,
                        'new_order': new_order,
                        'idx': len(chapter_tasks)
                    })
            else:
                # 只有一个目录项，按原逻辑处理
                processed_hrefs.add(href_base)
                toc_entry = toc_entries[0]
                new_order = toc_entry['order'] + order_offset
                chapter_tasks.append({
                    'toc_entry': toc_entry,
                    'item': item,
                    'href_base': href_base,
                    'new_order': new_order,
                    'idx': len(chapter_tasks)
                })

        # 补充处理：只有当 NCX 目录严重不完整时才添加未在目录中的 spine 文件
        # 判断标准：目录项数量少于 spine 数量的 30% 或者少于 10 个
        if len(chapter_tasks) > 0:
            spine_count = len(book.spine) if book.spine else 0
            toc_count = len(toc_hierarchy)

            if spine_count > 0 and (toc_count < spine_count * 0.3 or toc_count < 10):
                logger.debug(f"NCX 目录不完整 (目录项 {toc_count} vs spine {spine_count})，检查是否需要补充")

                all_spine_hrefs = set()
                for spine_item in book.spine:
                    if isinstance(spine_item, tuple):
                        item_id = spine_item[0]
                    else:
                        item_id = str(spine_item)

                    for item in book.get_items():
                        if item.get_type() == 9 and item.get_id() == item_id:
                            spine_href = item.get_name()
                            all_spine_hrefs.add(spine_href)
                            break

                processed_toc_hrefs = set()
                for toc_entry in toc_hierarchy:
                    href_base = toc_entry['href'].split('#')[0]
                    processed_toc_hrefs.add(href_base)

                remaining_spine_hrefs = all_spine_hrefs - processed_toc_hrefs
                if remaining_spine_hrefs:
                    logger.debug(f"发现 {len(remaining_spine_hrefs)} 个未在目录中的 spine 文件")
                    for i, spine_href in enumerate(sorted(remaining_spine_hrefs)):
                        item = items_by_name.get(spine_href)
                        if item:
                            new_order = order_offset + len(chapter_tasks) + i + 1
                            chapter_tasks.append({
                                'toc_entry': {
                                    'title': f'第{new_order}章',
                                    'href': spine_href,
                                    'level': 0,
                                    'order': new_order,
                                    'parent_href': ''
                                },
                                'item': item,
                                'href_base': spine_href,
                                'new_order': new_order,
                                'idx': len(chapter_tasks)
                            })

        # 使用线程池并行处理章节内容提取
        if chapter_tasks:
            logger.info(f"开始并行处理 {len(chapter_tasks)} 个章节，使用{self.chapter_workers}线程")
            with ThreadPoolExecutor(max_workers=self.chapter_workers) as executor:
                future_to_task = {
                    executor.submit(
                        self._extract_chapter_content_task,
                        task['item'],
                        task['new_order'],
                        task['toc_entry'],
                        task['href_base']
                    ): task for task in chapter_tasks
                }
                
                completed = 0
                # 用于跟踪每个 href_base 的第一个章节 temp_id（用于设置 parent_id）
                href_first_chapter_id = {}

                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    chapter = future.result()
                    if chapter:
                        # 设置parent_id
                        if chapter.level > 0:
                            parent_href = task['toc_entry'].get('parent_href', '')
                            if parent_href:
                                parent_href = parent_href.split('#')[0]
                                # 查找父章节的 temp_id
                                if parent_href in href_first_chapter_id:
                                    chapter.parent_id = href_first_chapter_id[parent_href]

                        temp_id = str(uuid.uuid4())
                        chapter.temp_id = temp_id
                        chapters.append(chapter)

                        # 记录第一个章节的 temp_id（用于子章节的 parent_id）
                        if task['href_base'] not in href_first_chapter_id:
                            href_first_chapter_id[task['href_base']] = temp_id

                    completed += 1
                    if progress_callback:
                        progress_callback(completed, len(chapter_tasks))
        
        # 按order排序章节
        chapters.sort(key=lambda x: x.order)

        # 修复parent_id：创建 href -> chapter 映射，然后为所有子章节设置正确的parent_id
        # 同一href可能被多个章节使用（一级和二级都指向同一个HTML文件），需要选择层级最低的作为父章节
        href_to_chapter = {}
        for ch in chapters:
            href_key = ch.href.split('#')[0] if ch.href else ''
            if href_key:
                if href_key not in href_to_chapter:
                    href_to_chapter[href_key] = ch
                else:
                    existing = href_to_chapter[href_key]
                    if ch.level < existing.level:
                        href_to_chapter[href_key] = ch

        for ch in chapters:
            if ch.level > 0:
                toc_entry = None
                ch_href_base = ch.href.split('#')[0] if ch.href else ''
                ch_order = int(ch.order) if ch.order else 0
                for task in chapter_tasks:
                    task_toc = task.get('toc_entry', {})
                    task_href_base = task.get('href_base', '')
                    task_level = task_toc.get('level', -1)
                    task_order = int(task_toc.get('order', 0))

                    if task_href_base == ch_href_base and task_level == ch.level and abs(task_order - ch_order) < 5:
                        toc_entry = task_toc
                        break

                if not toc_entry:
                    for task in chapter_tasks:
                        if task['href_base'] == ch_href_base:
                            toc_entry = task.get('toc_entry', {})
                            break

                if toc_entry:
                    parent_href_raw = toc_entry.get('parent_href', '')
                    if parent_href_raw:
                        parent_href = parent_href_raw.split('#')[0]
                        parent_chapter = href_to_chapter.get(parent_href)
                        if parent_chapter:
                            ch.parent_id = parent_chapter.temp_id

        return chapters
    
    def _extract_chapter_content_task(self, item, new_order, toc_entry, href_base):
        """单个章节内容提取任务（用于多线程）"""
        try:
            full_href = toc_entry.get('href', href_base)
            anchor_id = None
            if '#' in full_href:
                parts = full_href.split('#')
                anchor_id = parts[1] if len(parts) > 1 else None
                href_base = parts[0]

            soup = BeautifulSoup('<div></div>', 'html.parser')
            combined_soup = soup

            is_split_file = False
            split_base = None

            if '_split_' in href_base:
                match = re.search(r'(.+)_split_\d+', href_base)
                if match:
                    split_base = match.group(1)
                    is_split_file = bool(re.search(r'part\d+_split_', href_base))

            logger.debug(f"处理章节 {toc_entry.get('title', '')}: href_base={href_base}, is_split_file={is_split_file}")

            if is_split_file:
                base_pattern = href_base.split('_split_')[0] + '_split_'
                logger.debug(f"检测到_split_文件，查找所有相关文件: {base_pattern}*")

                if hasattr(self, 'current_book') and self.current_book:
                    split_items = []
                    for book_item in self.current_book.get_items():
                        if book_item.get_type() == 9:
                            item_name = book_item.get_name()
                            if item_name.startswith(base_pattern):
                                split_items.append((item_name, book_item))

                    split_items.sort(key=lambda x: x[0])
                    logger.debug(f"找到 {len(split_items)} 个_split_文件")

                    for split_name, split_item in split_items:
                        split_content = split_item.get_content()
                        split_soup = BeautifulSoup(split_content, 'html.parser')

                        if anchor_id and split_name == href_base:
                            anchor_elem = split_soup.find(id=anchor_id)
                            if anchor_elem:
                                extracted = self._extract_content_by_anchor(split_soup, anchor_id)
                                if extracted:
                                    for child in extracted.find_all(recursive=False):
                                        combined_soup.find('div').append(child)
                                    anchor_id = None
                            continue

                        body = split_soup.find('body')
                        if body:
                            for child in body.children:
                                if hasattr(child, 'name') and child.name and child.name not in ['nav', 'style', 'script']:
                                    combined_soup.find('div').append(child)
                        else:
                            for child in split_soup.find_all(recursive=False):
                                if hasattr(child, 'name') and child.name and child.name not in ['nav', 'style', 'script']:
                                    combined_soup.find('div').append(child)
            else:
                soup = BeautifulSoup(item.get_content(), 'html.parser')

                if anchor_id:
                    anchor_elem = soup.find(id=anchor_id)
                    if anchor_elem:
                        extracted_soup = self._extract_content_by_anchor(soup, anchor_id)
                        if extracted_soup:
                            soup = extracted_soup

                combined_soup = soup

            content_result = self._extract_content_with_images(combined_soup, new_order)

            chapter = EPUBChapter(
                name=toc_entry['title'],
                order=new_order,
                level=toc_entry['level'],
                parent_id=None,
                href=href_base,
                paragraphs=content_result['paragraphs'],
                image_refs=content_result['image_refs'],
                html_content=str(combined_soup)
            )
            return chapter
        except Exception as e:
            logger.error(f"提取章节内容失败: {toc_entry.get('title', 'unknown')}, 错误: {e}")
            return None

    def _extract_content_by_anchor(self, soup, anchor_id):
        """根据锚点 ID 提取对应的内容片段"""
        try:
            anchor_elem = soup.find(id=anchor_id)
            if not anchor_elem:
                return None

            result_soup = BeautifulSoup('<div></div>', 'html.parser')
            result_div = result_soup.find('div')

            header_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7']

            elements_to_extract = []
            current = anchor_elem
            while current:
                elements_to_extract.append(current)

                next_elem = current.find_next_sibling()

                if next_elem and next_elem.name in header_tags:
                    header_level = int(next_elem.name[1]) if next_elem.name[1:].isdigit() else 0
                    anchor_level = int(anchor_elem.name[1]) if anchor_elem.name[1:].isdigit() and anchor_elem.name.startswith('h') else 0

                    if header_level <= anchor_level:
                        break

                if not next_elem:
                    break
                current = next_elem

            for elem in elements_to_extract:
                result_div.append(copy.copy(elem))

            return result_soup
        except Exception as e:
            logger.debug(f"提取锚点内容失败: {e}")
            return None

    def _extract_content_with_images(self, soup, chapter_order: int) -> Dict:
        """提取章节内容，包括文本、图片、表格和脚注"""
        content_items = []
        
        all_imgs = soup.find_all('img')
        logger.debug(f"章节{chapter_order}找到 {len(all_imgs)} 个img标签")

        footnote_elements = soup.find_all(class_=lambda x: x and ('footnote' in x.lower() or 'note' in x.lower()))
        footnote_ids = set()
        for elem in footnote_elements:
            if elem.get('id'):
                footnote_ids.add(elem.get('id'))
        
        processed_elements = set()
        
        # 按文档流顺序递归处理所有元素
        def process_element(element):
            """递归处理元素，保持文档流顺序"""
            if element in processed_elements:
                return

            # 跳过脚本、样式、注释等
            if element.name in ['script', 'style', 'comment', 'nav']:
                processed_elements.add(element)
                return

            # 处理 img 元素（优先处理，不受父元素影响）
            if element.name == 'img':
                src = element.get('src', '')
                alt = element.get('alt', '')
                if src:
                    content_items.append({
                        'type': 'image',
                        'src': src,
                        'alt': alt
                    })
                processed_elements.add(element)
                return

            # 处理 figure 元素
            if element.name == 'figure':
                # 找出所有直接子代的 img
                for child in element.children:
                    if hasattr(child, 'name') and child.name == 'img':
                        src = child.get('src', '')
                        alt = child.get('alt', '')
                        if src:
                            content_items.append({
                                'type': 'image',
                                'src': src,
                                'alt': alt
                            })
                        processed_elements.add(child)

                figcaption = element.find('figcaption')
                if figcaption:
                    text = figcaption.get_text().strip()
                    if text:
                        cleaned = clean_text(text)
                        if cleaned:
                            content_items.append({
                                'type': 'text',
                                'content': cleaned
                            })
                processed_elements.add(element)
                return

            # 处理 SVG 图片
            if element.name == 'svg':
                svg_image = element.find('image')
                if svg_image:
                    xlink_href = svg_image.get('xlink:href') or svg_image.get('{http://www.w3.org/1999/xlink}href')
                    href = svg_image.get('href')
                    src = xlink_href or href
                    if src:
                        content_items.append({
                            'type': 'image',
                            'src': src,
                            'alt': '封面图片'
                        })
                processed_elements.add(element)
                return

            # 处理链接 (目录页中的链接)
            if element.name == 'a':
                text = element.get_text(strip=True)
                href = element.get('href', '')
                if text and href:
                    cleaned = clean_text(text)
                    if cleaned and len(cleaned) > 1:
                        content_items.append({
                            'type': 'text',
                            'content': cleaned,
                            'is_footnote': False
                        })
                processed_elements.add(element)
                return

            # 处理表格
            if element.name == 'table':
                table_data = self._extract_table(element)
                if table_data:
                    content_items.append({
                        'type': 'table',
                        'content': table_data
                    })
                processed_elements.add(element)
                return

            # 处理文本块级元素
            if element.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'li', 'pre']:
                # 跳过嵌套在表格、figure中的
                for parent in element.parents:
                    if parent.name in ['table', 'figure']:
                        processed_elements.add(element)
                        return

                # 先提取嵌套在元素内的图片（处理 <p><sup><a><img> 等嵌套结构）
                nested_imgs = element.find_all('img')
                for img in nested_imgs:
                    src = img.get('src', '')
                    alt = img.get('alt', '')
                    if src and src not in [item['src'] for item in content_items if item['type'] == 'image']:
                        content_items.append({
                            'type': 'image',
                            'src': src,
                            'alt': alt
                        })
                        processed_elements.add(img)

                is_footnote = False
                elem_id = element.get('id', '')
                elem_class = ' '.join(element.get('class', []))
                if elem_id in footnote_ids or 'footnote' in elem_class.lower() or 'note' in elem_class.lower():
                    is_footnote = True

                text = self._extract_text_with_formatting(element)
                if text:
                    cleaned = clean_text(text)
                    if cleaned:
                        content_items.append({
                            'type': 'text',
                            'content': cleaned,
                            'is_footnote': is_footnote
                        })
                processed_elements.add(element)
                return

            # 处理 div - 处理所有子元素
            if element.name == 'div':
                # 找出所有直接块级子元素
                block_children = []
                for child in element.children:
                    if hasattr(child, 'name') and child.name:
                        if child.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'figure', 'table', 'img', 'blockquote', 'li', 'pre']:
                            block_children.append(child)

                if block_children:
                    # 有块级子元素，递归处理子元素
                    for child in block_children:
                        process_element(child)
                    processed_elements.add(element)
                    return

                # 没有块级子元素，提取直接文本
                direct_text = ''
                for child in element.children:
                    if isinstance(child, NavigableString):
                        direct_text += str(child)

                direct_text = direct_text.strip()
                if direct_text and len(direct_text) > 0:
                    cleaned = clean_text(direct_text)
                    if cleaned:
                        content_items.append({
                            'type': 'text',
                            'content': cleaned,
                            'is_footnote': False
                        })
                processed_elements.add(element)
                return

            # 递归处理其他元素的子元素
            for child in element.children:
                if hasattr(child, 'name') and child.name:
                    process_element(child)
        
        # 从 body 开始递归处理，保持文档流顺序
        body = soup.find('body')
        if body:
            self._process_body_children(body, process_element)
        else:
            # 没有 body，从根元素开始
            for element in soup.find_all(recursive=False):
                if hasattr(element, 'name') and element.name:
                    process_element(element)

        paragraphs = []
        image_refs = []

        for idx, item in enumerate(content_items):
            order = idx + 1
            if item['type'] == 'image':
                image_refs.append({
                    'src': item['src'],
                    'alt': item.get('alt', ''),
                    'order': order
                })
                paragraphs.append({
                    'type': 'image',
                    'content': item['src'],
                    'alt': item.get('alt', ''),
                    'is_footnote': False
                })
            else:
                if item['type'] == 'table':
                    paragraphs.append({
                        'type': 'table',
                        'content': item['content'],
                        'is_footnote': False
                    })
                else:
                    paragraphs.append({
                        'type': 'text',
                        'content': item['content'],
                        'is_footnote': item.get('is_footnote', False)
                    })

        return {
            'paragraphs': paragraphs,
            'image_refs': image_refs
        }

    def _process_body_children(self, parent, process_element):
        """递归处理 body 的子元素，包括嵌套在 div 等容器中的元素"""
        for child in parent.children:
            if not hasattr(child, 'name') or not child.name:
                continue

            if child.name in ['div', 'section', 'article', 'span']:
                process_element(child)
                self._process_body_children(child, process_element)
            else:
                process_element(child)

    def _extract_text_with_formatting(self, element) -> str:
        """提取元素中的文本，保留格式标记"""
        text_parts = []
        
        def process_node(node, in_bold=False, in_italic=False, in_sup=False, in_sub=False):
            if isinstance(node, NavigableString):
                text = str(node).strip()
                if text:
                    if in_bold:
                        text = f"**{text}**"
                    if in_italic:
                        text = f"*{text}*"
                    if in_sup:
                        text = f"^{text}^"
                    if in_sub:
                        text = f"~{text}~"
                    text_parts.append(text)
                return
            
            if node.name in ['script', 'style', 'nav', 'footer', 'header']:
                return
            
            new_bold = in_bold or node.name in ['b', 'strong']
            new_italic = in_italic or node.name in ['i', 'em']
            new_sup = in_sup or node.name == 'sup'
            new_sub = in_sub or node.name == 'sub'
            
            for child in node.children:
                process_node(child, new_bold, new_italic, new_sup, new_sub)
        
        process_node(element)
        
        return ' '.join(text_parts)

    def _extract_table(self, table_element) -> Optional[Dict]:
        try:
            headers = []
            rows = []

            thead = table_element.find('thead')
            if thead:
                header_row = thead.find('tr')
                if header_row:
                    for th in header_row.find_all(['th', 'td']):
                        headers.append(th.get_text().strip())
            
            tbody = table_element.find('tbody')
            if not tbody:
                tbody = table_element
            
            for tr in tbody.find_all('tr'):
                row = []
                for td in tr.find_all(['td', 'th']):
                    cell_text = td.get_text().strip()
                    row.append(cell_text)
                if row:
                    rows.append(row)
            
            if not rows:
                return None

            return {
                'headers': headers,
                'rows': rows
            }
        except Exception as e:
            logger.warning(f"提取表格失败: {e}")
            return None

    def extract_images_from_epub(self, book, chapters: List[EPUBChapter], book_id: str, file_path: str = None):
        image_items = {}
        
        total_items = 0
        image_type_count = 0
        type_counts = {}

        for item in book.get_items():
            total_items += 1
            item_type = item.get_type()
            type_counts[item_type] = type_counts.get(item_type, 0) + 1
            if item_type == 1 or item_type == 4:
                image_type_count += 1
                href = None
                
                try:
                    href = item.get_name()
                except:
                    pass
                
                if not href:
                    try:
                        href = item.file_name
                    except:
                        pass
                
                if not href:
                    item_str = str(item)
                    if 'EpubImage' in item_str:
                        parts = item_str.split(':')
                        if len(parts) >= 3:
                            href = parts[-1]
                
                if not href:
                    logger.warning(f"无法获取href, item_type={item_type}, item={item}")
                    continue
                
                try:
                    content = item.get_content()
                    if not content:
                        logger.warning(f"内容为空, href={href}")
                        continue
                    image_items[href] = content
                    basename = href.split('/')[-1]
                    image_items[basename] = content
                    logger.debug(f"成功收集图片: href={href}, basename={basename}, content_len={len(content)}")
                except Exception as e:
                    logger.warning(f"获取内容失败: {e}, href={href}")
        
        # 从zip文件中读取不在manifest中的图片（如cover.jpg）
        if file_path and os.path.exists(file_path):
            try:
                with zipfile.ZipFile(file_path, 'r') as zf:
                    for name in zf.namelist():
                        # 检查是否是图片文件
                        if name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg')):
                            # 如果不在已收集的图片中，则添加
                            if name not in image_items and name.split('/')[-1] not in image_items:
                                try:
                                    content = zf.read(name)
                                    if content:
                                        image_items[name] = content
                                        basename = name.split('/')[-1]
                                        image_items[basename] = content
                                        logger.debug(f"从zip文件收集图片: {name}, basename={basename}, content_len={len(content)}")
                                except Exception as e:
                                    logger.warning(f"从zip读取图片失败: {name}, 错误: {e}")
            except Exception as e:
                logger.warning(f"打开zip文件失败: {e}")
        
        logger.debug(f"EPUB共有 {total_items} 个item, 收集到 {len(image_items)} 张图片")

        # 收集所有需要处理的图片任务
        image_tasks = []
        saved_images = set()
        total_image_refs = 0
        matched_count = 0

        for chapter in chapters:
            total_image_refs += len(chapter.image_refs)
            for img_ref in chapter.image_refs:
                src = img_ref.get('src', '')
                alt = img_ref.get('alt', '')

                if src.startswith('data:'):
                    continue
                
                src_cleaned = src.replace('../', '').replace('./', '').lstrip('/')
                src_basename = src.split('/')[-1].lower()

                image_data = None
                original_format = None
                matched_href = None

                # 尝试匹配图片
                for href, content in image_items.items():
                    href_cleaned = href.replace('../', '').replace('./', '').lstrip('/')
                    href_basename = href.split('/')[-1].lower()
                    
                    if (src == href or 
                        src_cleaned == href_cleaned or
                        src_cleaned == href or
                        src == href_cleaned or
                        src_basename == href_basename or
                        src.endswith(href) or href.endswith(src) or
                        src_cleaned.endswith(href_cleaned) or href_cleaned.endswith(src_cleaned)):
                        image_data = content
                        original_format = href.split('.')[-1].lower() if '.' in href else 'unknown'
                        matched_href = href
                        matched_count += 1
                        break
                
                if not image_data:
                    for href, content in image_items.items():
                        href_basename_lower = href.split('/')[-1].lower()
                        if src_basename == href_basename_lower:
                            image_data = content
                            original_format = href.split('.')[-1].lower() if '.' in href else 'unknown'
                            matched_href = href
                            matched_count += 1
                            break
                
                if not image_data:
                    continue

                image_key = f"{chapter.order}_{src}"
                if image_key in saved_images:
                    continue
                
                saved_images.add(image_key)
                image_tasks.append({
                    'image_data': image_data,
                    'book_id': book_id,
                    'chapter_order': chapter.order,
                    'image_order': img_ref['order'],
                    'original_format': original_format,
                    'src': src,
                    'alt': alt,
                    'image_key': image_key
                })

        # 使用线程池并行处理图片保存
        image_data_list = []
        if image_tasks:
            logger.debug(f"开始并行处理 {len(image_tasks)} 张图片，使用{self.image_workers}线程")
            with ThreadPoolExecutor(max_workers=self.image_workers) as executor:
                future_to_task = {
                    executor.submit(
                        self._save_image_task,
                        task['image_data'],
                        task['book_id'],
                        task['chapter_order'],
                        task['image_order'],
                        task['original_format'],
                        task['src'],
                        task['alt']
                    ): task for task in image_tasks
                }
                
                for future in as_completed(future_to_task):
                    result = future.result()
                    if result:
                        image_data_list.append(result)

        logger.info(f"图片处理统计: 总引用={total_image_refs}, 匹配成功={matched_count}, 保存成功={len(image_data_list)}")
        return image_data_list
    
    def _save_image_task(self, image_data, book_id, chapter_order, image_order, original_format, src, alt):
        """单个图片保存任务（用于多线程）"""
        try:
            result = self.image_processor.save_image(
                image_data, book_id, f"chapter_{chapter_order}",
                image_order, original_format
            )
            if result:
                path, width, height, fmt = result
                return {
                    'path': path,
                    'width': width,
                    'height': height,
                    'alt': alt,
                    'order': image_order,
                    'original_format': fmt,
                    'chapter_order': chapter_order,
                    'original_src': src
                }
        except Exception as e:
            logger.warning(f"保存图片失败: {src}, 错误: {e}")
        return None

    def extract_cover(self, book, book_id: str, file_path: str = None) -> Optional[str]:
        """提取EPUB封面图片"""
        try:
            cover_data = None
            cover_href = None

            # 方法1: 检查 manifest 中的 cover-image 属性
            for item in book.get_items():
                if item.get_type() == 2:  # OPF 文件
                    try:
                        content = item.get_content()
                        soup = BeautifulSoup(content, 'xml')

                        # 查找 properties 包含 cover-image 的 item
                        items = soup.find_all('item', {'media-type': lambda x: x and x.startswith('image/')})
                        for img_item in items:
                            props = img_item.get('properties', '')
                            if 'cover-image' in props:
                                cover_href = img_item.get('href', '')
                                # 找到 href 后，需要从 manifest 中找到对应的图片
                                manifest_items = {it.get('id'): it for it in book.get_items() if it.get_type() in [1, 4]}
                                for manifest_item in book.get_items():
                                    try:
                                        if manifest_item.get_name() == cover_href or manifest_item.get_id() == cover_href:
                                            cover_data = manifest_item.get_content()
                                            logger.debug(f"通过 manifest cover-image 属性找到封面: {cover_href}")
                                            break
                                    except:
                                        pass
                                if cover_data:
                                    break
                    except Exception as e:
                        logger.debug(f"检查 manifest cover-image 失败: {e}")
                if cover_data:
                    break

            # 方法2: 使用 get_cover 方法
            if not cover_data and hasattr(book, 'get_cover'):
                try:
                    cover_data = book.get_cover()
                    if cover_data:
                        logger.debug("通过get_cover方法获取封面")
                except:
                    pass

            # 方法3: 检查 manifest 中 id 为 "cover-image" 的项
            if not cover_data:
                for item in book.get_items():
                    item_type = item.get_type()
                    if item_type == 1 or item_type == 4:
                        try:
                            item_id = item.get_id()
                            if item_id and 'cover' in item_id.lower():
                                cover_data = item.get_content()
                                try:
                                    cover_href = item.get_name()
                                except:
                                    cover_href = item.file_name
                                logger.debug(f"通过 cover-id 找到封面: {item_id}, href={cover_href}")
                                break
                        except:
                            pass

            # 方法4: 从 spine 第一项获取封面图片
            if not cover_data and book.spine:
                try:
                    spine_item = book.spine[0]
                    if isinstance(spine_item, tuple):
                        item_id = spine_item[0]
                    else:
                        item_id = str(spine_item)

                    # 找到对应的 HTML 内容
                    for item in book.get_items():
                        if item.get_type() == 9 and item.get_id() == item_id:
                            content = item.get_content()
                            soup = BeautifulSoup(content, 'html.parser')
                            imgs = soup.find_all('img')
                            if imgs:
                                # 获取第一个图片的 src
                                img_src = imgs[0].get('src', '')
                                if img_src:
                                    # 从 manifest 中找到对应的图片
                                    base_href = os.path.dirname(item.get_name()) if item.get_name() else ''
                                    if base_href and not img_src.startswith('/'):
                                        img_full_path = os.path.join(base_href, img_src)
                                    else:
                                        img_full_path = img_src

                                    # 规范化路径
                                    img_full_path = img_full_path.replace('\\', '/')
                                    if not img_full_path.startswith('/'):
                                        pass

                                    # 在 manifest 中查找
                                    for img_item in book.get_items():
                                        if img_item.get_type() in [1, 4]:
                                            try:
                                                img_name = img_item.get_name()
                                                if img_name == img_src or img_name.endswith(img_src) or img_src.endswith(img_name):
                                                    cover_data = img_item.get_content()
                                                    cover_href = img_name
                                                    logger.debug(f"从 spine 第一项找到封面: {img_name}")
                                                    break
                                            except:
                                                pass
                                    if cover_data:
                                        break
                            break
                except Exception as e:
                    logger.debug(f"从 spine 获取封面失败: {e}")

            # 方法5: 通过 cover 关键字查找
            if not cover_data:
                for item in book.get_items():
                    item_type = item.get_type()
                    if item_type == 1 or item_type == 4:
                        href = None
                        try:
                            href = item.get_name()
                        except:
                            pass
                        if not href:
                            try:
                                href = item.file_name
                            except:
                                pass
                        
                        if href:
                            href_lower = href.lower()
                            if 'cover' in href_lower:
                                try:
                                    cover_data = item.get_content()
                                    cover_href = href
                                    logger.debug(f"通过cover关键字找到封面: {href}")
                                    break
                                except:
                                    pass
            
            # 从zip文件中查找cover图片（不在manifest中的情况）
            if not cover_data and file_path and os.path.exists(file_path):
                try:
                    with zipfile.ZipFile(file_path, 'r') as zf:
                        # 优先查找包含cover的图片
                        for name in zf.namelist():
                            if 'cover' in name.lower() and name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                                try:
                                    cover_data = zf.read(name)
                                    cover_href = name
                                    logger.debug(f"从zip文件找到封面: {name}")
                                    break
                                except:
                                    pass
                except Exception as e:
                    logger.warning(f"从zip文件查找封面失败: {e}")
            
            if not cover_data:
                for item in book.get_items():
                    item_type = item.get_type()
                    if item_type == 1 or item_type == 4:
                        try:
                            cover_data = item.get_content()
                            href = None
                            try:
                                href = item.get_name()
                            except:
                                pass
                            if not href:
                                try:
                                    href = item.file_name
                                except:
                                    pass
                            cover_href = href
                            logger.debug(f"使用第一个图片作为封面: {href}")
                            break
                        except:
                            pass
            
            if cover_data:
                result = self.image_processor.save_image(
                    cover_data, book_id, "cover",
                    1, cover_href.split('.')[-1] if cover_href and '.' in cover_href else None
                )
                
                if result:
                    path, width, height, fmt = result
                    logger.debug(f"封面保存成功: {path}, 尺寸: {width}x{height}")
                    return path
            
            logger.warning("未找到封面图片")
            return None
            
        except Exception as e:
            logger.error(f"提取封面失败: {e}")
            return None
