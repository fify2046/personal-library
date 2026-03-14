import os
import logging
import uuid
import re
import json
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from ebooklib import epub
from bs4 import BeautifulSoup, NavigableString
from image_processor import clean_text

logger = logging.getLogger(__name__)


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
    def __init__(self, image_processor):
        self.image_processor = image_processor
        self.ncx_ns = {'ncx': 'http://www.daisy.org/z3986/2005/ncx/'}

    def extract(self, file_path: str, book_id: str, progress_callback=None) -> Tuple[bool, str, Dict]:
        try:
            book = epub.read_epub(file_path, {'ignore_ncx': False})
            logger.info(f"EPUB文件打开成功: {file_path}")

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
        """直接解析NCX文件获取层级目录"""
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                ncx_files = [f for f in zf.namelist() if f.endswith('.ncx')]
                
                if not ncx_files:
                    logger.warning("未找到NCX文件")
                    return []
                
                ncx_content = zf.read(ncx_files[0])
                return self._parse_ncx_content(ncx_content)
                
        except Exception as e:
            logger.error(f"解析NCX失败: {e}")
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
                src = content_elem.get('src', '') if content_elem is not None else ""
                
                src = src.split('#')[0]
                
                order[0] += 1
                entry = {
                    'title': title,
                    'href': src,
                    'level': level,
                    'order': order[0],
                    'parent_href': parent_href
                }
                toc.append(entry)
                
                for child in nav_point.findall('ncx:navPoint', self.ncx_ns):
                    parse_nav_point(child, level + 1, src)
            
            for nav_point in nav_map.findall('ncx:navPoint', self.ncx_ns):
                parse_nav_point(nav_point, 0, "")
            
            logger.info(f"NCX解析完成，共 {len(toc)} 个目录项，层级分布: {dict((l, sum(1 for x in toc if x['level']==l)) for l in set(x['level'] for x in toc))}")
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
        
        logger.info(f"目录href数量: {len(toc_hrefs)}")
        
        # 构建 id -> item 映射
        items_by_id = {}
        for item in book.get_items():
            if item.get_type() == 9:
                items_by_id[item.get_id()] = item
        
        spine_pre_items = []
        try:
            if book.spine:
                logger.info(f"Spine项目数量: {len(book.spine)}")
                logger.info(f"Spine项目列表: {book.spine[:5]}...")
                for spine_idx, spine_item in enumerate(book.spine):
                    if isinstance(spine_item, tuple):
                        item_id = spine_item[0]
                    else:
                        item_id = str(spine_item)
                    
                    logger.info(f"处理Spine项目 {spine_idx}: item_id={item_id}")
                    
                    # 首先通过 id 查找
                    spine_content_item = items_by_id.get(item_id)
                    if spine_content_item:
                        spine_href = spine_content_item.get_name()
                        logger.info(f"  通过id匹配到item: {spine_href}")
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
                                    logger.info(f"  通过name匹配到item: {item_name}")
                                    break
                                basename = os.path.basename(item_name)
                                if basename == item_id:
                                    spine_href = item_name
                                    spine_content_item = item
                                    logger.info(f"  通过basename匹配到item: {item_name}")
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
                        logger.info(f"Spine项目 {spine_idx} ({spine_href}) 在目录中匹配到 {matched_toc_href}，停止添加前置页面")
                        break
                    else:
                        logger.info(f"Spine项目 {spine_idx} ({spine_href}) 不在目录中，将作为前置页面添加")
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
                logger.info(f"添加前置章节: {chapter_name}, href={spine_href}")
        
        order_offset = pre_order
        
        for idx, toc_entry in enumerate(toc_hierarchy):
            if progress_callback:
                progress_callback(idx + 1, len(toc_hierarchy))
            
            href = toc_entry['href']
            
            href_base = href.split('#')[0]
            
            if href_base in processed_hrefs:
                continue
            processed_hrefs.add(href_base)
            
            item = items_by_name.get(href_base) or items_by_name.get(href)
            
            if not item:
                for name, it in items_by_name.items():
                    if name.endswith(href_base) or href_base.endswith(name):
                        item = it
                        break
            
            if not item:
                logger.warning(f"找不到章节内容: {href}")
                continue
            
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            
            new_order = toc_entry['order'] + order_offset
            content_result = self._extract_content_with_images(soup, new_order)
            
            temp_id = str(uuid.uuid4())
            
            parent_id = None
            if toc_entry['level'] > 0 and toc_entry['parent_href']:
                parent_href = toc_entry['parent_href'].split('#')[0]
                if parent_href in href_to_temp_id:
                    parent_id = href_to_temp_id[parent_href]
            
            chapter = EPUBChapter(
                name=toc_entry['title'],
                order=new_order,
                level=toc_entry['level'],
                parent_id=parent_id,
                href=href_base,
                paragraphs=content_result['paragraphs'],
                image_refs=content_result['image_refs'],
                html_content=str(soup)
            )
            chapter.temp_id = temp_id
            chapters.append(chapter)
            href_to_temp_id[href_base] = temp_id
        
        return chapters

    def _extract_content_with_images(self, soup, chapter_order: int) -> Dict:
        """提取章节内容，包括文本、图片、表格和脚注"""
        content_items = []
        
        all_imgs = soup.find_all('img')
        logger.info(f"章节{chapter_order}找到 {len(all_imgs)} 个img标签")

        footnote_elements = soup.find_all(class_=lambda x: x and ('footnote' in x.lower() or 'note' in x.lower()))
        footnote_ids = set()
        for elem in footnote_elements:
            if elem.get('id'):
                footnote_ids.add(elem.get('id'))
        
        processed_elements = set()
        
        # 0. 处理 SVG 图片（封面常用）
        svg_elements = soup.find_all('svg')
        for svg in svg_elements:
            if svg in processed_elements:
                continue
            # 查找 SVG 中的 image 元素
            svg_image = svg.find('image')
            if svg_image:
                # 尝试获取 xlink:href 或 href 属性
                xlink_href = svg_image.get('xlink:href') or svg_image.get('{http://www.w3.org/1999/xlink}href')
                href = svg_image.get('href')
                src = xlink_href or href
                if src:
                    content_items.append({
                        'type': 'image',
                        'src': src,
                        'alt': '封面图片'
                    })
                    logger.info(f"章节{chapter_order}找到SVG图片: {src}")
            processed_elements.add(svg)
        
        # 1. 先处理 figure 元素（包含图片和figcaption）
        figure_elements = soup.find_all('figure')
        for element in figure_elements:
            if element in processed_elements:
                continue
            
            img = element.find('img')
            if img:
                src = img.get('src', '')
                alt = img.get('alt', '') or element.get('figcaption', '')
                if src:
                    content_items.append({
                        'type': 'image',
                        'src': src,
                        'alt': alt
                    })
                processed_elements.add(img)

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
        
        # 2. 处理不在 figure 中的 img 元素
        img_elements = soup.find_all('img')
        for element in img_elements:
            if element in processed_elements:
                continue
            
            src = element.get('src', '')
            alt = element.get('alt', '')
            if src:
                content_items.append({
                    'type': 'image',
                    'src': src,
                    'alt': alt
                })
            processed_elements.add(element)
        
        # 3. 处理表格
        table_elements = soup.find_all('table')
        for element in table_elements:
            if element in processed_elements:
                continue
            
            table_data = self._extract_table(element)
            if table_data:
                content_items.append({
                    'type': 'table',
                    'content': table_data
                })
            processed_elements.add(element)
        
        # 4. 处理文本元素 - 只处理块级元素，跳过容器元素
        text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'li', 'pre'])
        for element in text_elements:
            if element in processed_elements:
                continue
            
            # 跳过嵌套在其他已处理元素中的元素
            skip_due_to_parent = False
            for parent in element.parents:
                if parent in processed_elements:
                    skip_due_to_parent = True
                    break
                # 跳过嵌套在表格、figure中的元素
                if parent.name in ['table', 'figure']:
                    skip_due_to_parent = True
                    break
            
            if skip_due_to_parent:
                continue

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
        
        # 5. 处理 div 中的文本（扉页等页面常用）
        # 只处理那些直接包含文本（不是通过子元素）的 div
        div_elements = soup.find_all('div')
        for element in div_elements:
            if element in processed_elements:
                continue
            
            # 跳过嵌套在其他已处理元素中的元素
            skip_due_to_parent = False
            for parent in element.parents:
                if parent in processed_elements:
                    skip_due_to_parent = True
                    break
                # 跳过嵌套在表格、figure、svg中的元素
                if parent.name in ['table', 'figure', 'svg']:
                    skip_due_to_parent = True
                    break
            
            if skip_due_to_parent:
                continue
            
            # 检查div是否包含块级子元素（p, h1-h6等）
            # 如果包含，则跳过，因为子元素会被单独处理
            block_children = element.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div'], recursive=False)
            if block_children:
                # 如果div包含块级子元素，跳过，让子元素自己处理
                processed_elements.add(element)
                continue
            
            # 只获取div直接包含的文本（不包括子元素的文本）
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
                    logger.info(f"章节{chapter_order}从div提取文本: {cleaned[:50]}...")
            processed_elements.add(element)

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
                    logger.info(f"成功收集图片: href={href}, basename={basename}, content_len={len(content)}")
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
                                        logger.info(f"从zip文件收集图片: {name}, basename={basename}, content_len={len(content)}")
                                except Exception as e:
                                    logger.warning(f"从zip读取图片失败: {name}, 错误: {e}")
            except Exception as e:
                logger.warning(f"打开zip文件失败: {e}")
        
        logger.info(f"EPUB共有 {total_items} 个item, 类型分布: {type_counts}, 收集到 {len(image_items)} 张图片")
        logger.info(f"图片href列表: {list(image_items.keys())[:10]}...")

        image_data_list = []
        saved_images = set()
        total_image_refs = 0
        matched_count = 0

        for chapter in chapters:
            total_image_refs += len(chapter.image_refs)
            logger.info(f"章节{chapter.order}({chapter.name})有 {len(chapter.image_refs)} 个图片引用")
            for img_ref in chapter.image_refs:
                src = img_ref.get('src', '')
                alt = img_ref.get('alt', '')

                image_data = None
                original_format = None
                matched_href = None

                if src.startswith('data:'):
                    logger.info(f"跳过data:图片: {src[:50]}...")
                    continue
                
                src_cleaned = src.replace('../', '').replace('./', '').lstrip('/')
                src_basename = src.split('/')[-1].lower()
                logger.info(f"查找图片: src={src}, 清理后={src_cleaned}, basename={src_basename}")

                for href, content in image_items.items():
                    href_cleaned = href.replace('../', '').replace('./', '').lstrip('/')
                    href_basename = href.split('/')[-1].lower()
                    
                    if (src == href or 
                        src_cleaned == href_cleaned or
                        src_cleaned == href or
                        src == href_cleaned or
                        src_basename == href_basename or
                        src.endswith(href) or href.endswith(src) or
                        src_cleaned.endswith(href_cleaned) or href_cleaned.endswith(src_cleaned) or
                        href_cleaned.endswith(src_cleaned) or src_cleaned.endswith(href_cleaned)):
                        image_data = content
                        original_format = href.split('.')[-1].lower() if '.' in href else 'unknown'
                        matched_href = href
                        matched_count += 1
                        logger.info(f"匹配成功: src={src} <-> href={href}")
                        break
                
                if not image_data:
                    for href, content in image_items.items():
                        href_basename_lower = href.split('/')[-1].lower()
                        if src_basename == href_basename_lower:
                            image_data = content
                            original_format = href.split('.')[-1].lower() if '.' in href else 'unknown'
                            matched_href = href
                            matched_count += 1
                            logger.info(f"通过basename匹配成功: src={src} <-> href={href}")
                            break
                
                if not image_data:
                    logger.warning(f"未找到匹配的图片: src={src}, src_cleaned={src_cleaned}, src_basename={src_basename}")
                    logger.warning(f"可用的图片href: {list(image_items.keys())[:10]}")
                    continue

                image_key = f"{chapter.order}_{src}"
                if image_key in saved_images:
                    logger.info(f"图片已保存，跳过: {src}")
                    continue
                
                image_order = img_ref['order']
                result = self.image_processor.save_image(
                    image_data, book_id, f"chapter_{chapter.order}",
                    image_order, original_format
                )

                if result:
                    path, width, height, fmt = result
                    image_data_list.append({
                        'path': path,
                        'width': width,
                        'height': height,
                        'alt': alt,
                        'order': image_order,
                        'original_format': fmt,
                        'chapter_order': chapter.order,
                        'original_src': src
                    })
                    saved_images.add(image_key)
                    logger.info(f"图片保存成功: {src} -> {path}")
                else:
                    logger.warning(f"无法保存图片: {src}")

        logger.info(f"图片处理统计: 总引用={total_image_refs}, 匹配成功={matched_count}, 保存成功={len(image_data_list)}")
        return image_data_list

    def extract_cover(self, book, book_id: str, file_path: str = None) -> Optional[str]:
        """提取EPUB封面图片"""
        try:
            cover_data = None
            cover_href = None
            
            if hasattr(book, 'get_cover'):
                try:
                    cover_data = book.get_cover()
                    if cover_data:
                        logger.info("通过get_cover方法获取封面")
                except:
                    pass
            
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
                                    logger.info(f"通过cover关键字找到封面: {href}")
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
                                    logger.info(f"从zip文件找到封面: {name}")
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
                            logger.info(f"使用第一个图片作为封面: {href}")
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
                    logger.info(f"封面保存成功: {path}, 尺寸: {width}x{height}")
                    return path
            
            logger.warning("未找到封面图片")
            return None
            
        except Exception as e:
            logger.error(f"提取封面失败: {e}")
            return None
