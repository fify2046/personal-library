import os
import io
import uuid
import logging
from typing import Optional, Tuple, List
from PIL import Image
import hashlib

logger = logging.getLogger(__name__)


class ImageProcessor:
    def __init__(self, base_image_dir: str):
        self.base_image_dir = base_image_dir
        os.makedirs(self.base_image_dir, exist_ok=True)

    def get_book_image_dir(self, book_id: str) -> str:
        book_dir = os.path.join(self.base_image_dir, book_id)
        os.makedirs(book_dir, exist_ok=True)
        return book_dir

    def get_chapter_image_dir(self, book_id: str, chapter_id: str) -> str:
        chapter_dir = os.path.join(self.get_book_image_dir(book_id), chapter_id)
        os.makedirs(chapter_dir, exist_ok=True)
        return chapter_dir

    def save_image(self, image_data: bytes, book_id: str, chapter_id: str,
                   image_order: int, original_format: str = None) -> Optional[Tuple[str, int, int, str]]:
        try:
            chapter_dir = self.get_chapter_image_dir(book_id, chapter_id)

            img = Image.open(io.BytesIO(image_data))
            width, height = img.size

            ext = self._determine_extension(original_format, img.format)
            if ext is None:
                ext = 'png'

            original_format = original_format or img.format or 'unknown'

            filename = f"img_{image_order:04d}_{uuid.uuid4().hex[:8]}.{ext}"
            filepath = os.path.join(chapter_dir, filename)

            if ext in ['svg', 'svgz']:
                filepath = self._convert_svg(image_data, filepath, img)
                if filepath and os.path.exists(filepath):
                    with Image.open(filepath) as converted_img:
                        width, height = converted_img.size
                    original_format = f'svg->{ext}'
                else:
                    return None
            else:
                if img.mode == 'RGBA' and ext in ['jpg', 'jpeg']:
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    background.save(filepath, quality=95)
                else:
                    img.save(filepath, quality=95)

            relative_path = os.path.join(book_id, chapter_id, filename).replace('\\', '/')
            logger.info(f"图片保存成功: {relative_path}, 尺寸: {width}x{height}")

            return (relative_path, width, height, original_format)

        except Exception as e:
            logger.error(f"保存图片失败: {e}")
            return None

    def _determine_extension(self, original_format: str, pil_format: str) -> Optional[str]:
        if original_format:
            fmt = original_format.lower()
            if fmt in ['svg', 'svgz']:
                return 'png'
            elif fmt in ['jpg', 'jpeg', 'jfif']:
                return 'jpg'
            elif fmt in ['png', 'gif', 'bmp', 'tiff', 'tif', 'webp']:
                return fmt

        if pil_format:
            fmt = pil_format.lower()
            if fmt in ['jpeg', 'jpg']:
                return 'jpg'
            elif fmt in ['png', 'gif', 'bmp', 'tiff', 'webp']:
                return fmt

        return 'png'

    def _convert_svg(self, svg_data: bytes, output_path: str, img=None) -> Optional[str]:
        try:
            import cairosvg
            output_path = output_path.replace('.svg', '.png').replace('.svgz', '.png')
            cairosvg.svg2png(bytestring=svg_data, write_to=output_path)
            logger.info(f"SVG转PNG成功: {output_path}")
            return output_path
        except ImportError:
            logger.warning("cairosvg未安装，尝试使用备用方法")
            return self._convert_svg_fallback(svg_data, output_path)
        except Exception as e:
            logger.error(f"SVG转换失败: {e}")
            return self._convert_svg_fallback(svg_data, output_path)

    def _convert_svg_fallback(self, svg_data: bytes, output_path: str) -> Optional[str]:
        try:
            output_path = output_path.replace('.svg', '.png').replace('.svgz', '.png')
            with open(output_path.replace('.png', '.svg'), 'wb') as f:
                f.write(svg_data)
            logger.warning(f"SVG文件已保存为临时文件: {output_path}")
            return None
        except Exception as e:
            logger.error(f"SVG备用转换失败: {e}")
            return None

    def save_pdf_image(self, xref: int, doc, book_id: str, chapter_id: str,
                       image_order: int) -> Optional[Tuple[str, int, int, str]]:
        try:
            img_dict = doc.extract_image(xref)
            image_data = img_dict.get('image')
            if not image_data:
                return None

            width = img_dict.get('width', 0)
            height = img_dict.get('height', 0)
            ext = img_dict.get('ext', 'png')

            chapter_dir = self.get_chapter_image_dir(book_id, chapter_id)
            filename = f"img_{image_order:04d}_{uuid.uuid4().hex[:8]}.{ext}"
            filepath = os.path.join(chapter_dir, filename)

            with open(filepath, 'wb') as f:
                f.write(image_data)

            relative_path = os.path.join(book_id, chapter_id, filename).replace('\\', '/')
            logger.info(f"PDF图片保存成功: {relative_path}")

            return (relative_path, width, height, ext)

        except Exception as e:
            logger.error(f"保存PDF图片失败: {e}")
            return None

    def check_write_permission(self, path: str) -> bool:
        try:
            test_file = os.path.join(path, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            return True
        except Exception:
            return False


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace('\r\n', '\n').replace('\r', '\n')

    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line:
            cleaned_lines.append(line)

    text = '\n'.join(cleaned_lines)

    text = ''.join(char for char in text if char.isprintable() or char in '\n\t')

    while '\n\n\n' in text:
        text = text.replace('\n\n\n', '\n\n')

    return text.strip()


def merge_paragraphs(text: str) -> str:
    if not text:
        return ""

    lines = text.split('\n')
    paragraphs = []
    current_para = []

    paragraph_indicators = [
        '。', '！', '？', '；', '……', '——', '」', '』', '】', '》',
        '.', '!', '?', ';', '...', '—', '"', "'", ')', ']', '}'
    ]

    for line in lines:
        line = line.strip()
        if not line:
            if current_para:
                paragraphs.append(''.join(current_para))
                current_para = []
            continue

        current_para.append(line)

        if any(line.endswith(indicator) for indicator in paragraph_indicators):
            if current_para:
                paragraphs.append(''.join(current_para))
                current_para = []

    if current_para:
        paragraphs.append(''.join(current_para))

    return '\n\n'.join(paragraphs)
