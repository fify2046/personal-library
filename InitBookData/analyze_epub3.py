import os
import zipfile
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

def parse_ncx_file(ncx_content):
    """直接解析NCX文件的层级结构"""
    root = ET.fromstring(ncx_content)
    
    ns = {
        'ncx': 'http://www.daisy.org/z3986/2005/ncx/'
    }
    
    nav_map = root.find('ncx:navMap', ns)
    if nav_map is None:
        return []
    
    def parse_nav_point(nav_point, level=0):
        results = []
        text_elem = nav_point.find('ncx:navLabel/ncx:text', ns)
        content_elem = nav_point.find('ncx:content', ns)
        
        title = text_elem.text if text_elem is not None else ""
        src = content_elem.get('src', '') if content_elem is not None else ""
        
        results.append({
            'level': level,
            'title': title,
            'src': src
        })
        
        for child in nav_point.findall('ncx:navPoint', ns):
            results.extend(parse_nav_point(child, level + 1))
        
        return results
    
    toc = []
    for nav_point in nav_map.findall('ncx:navPoint', ns):
        toc.extend(parse_nav_point(nav_point, 0))
    
    return toc

def analyze_epub_ncx(file_path):
    print(f"\n{'='*60}")
    print(f"分析EPUB的NCX目录: {os.path.basename(file_path)}")
    print(f"{'='*60}")
    
    with zipfile.ZipFile(file_path, 'r') as zf:
        ncx_files = [f for f in zf.namelist() if f.endswith('.ncx')]
        
        if not ncx_files:
            print("  未找到NCX文件")
            return
        
        for ncx_file in ncx_files:
            print(f"\n【NCX文件: {ncx_file}】")
            print("-" * 40)
            
            ncx_content = zf.read(ncx_file)
            toc = parse_ncx_file(ncx_content)
            
            print(f"  总共 {len(toc)} 个目录项")
            
            level_counts = {}
            for item in toc:
                lvl = item['level']
                level_counts[lvl] = level_counts.get(lvl, 0) + 1
            print(f"  层级分布: {level_counts}")
            
            print("\n  完整目录树:")
            for item in toc[:50]:
                indent = "  " * item['level']
                print(f"{indent}[L{item['level']}] {item['title'][:50]} -> {item['src'][:40]}")
            
            if len(toc) > 50:
                print(f"  ... 还有 {len(toc) - 50} 项")

def analyze_epub_content_detail(file_path):
    print(f"\n{'='*60}")
    print(f"分析EPUB内容提取: {os.path.basename(file_path)}")
    print(f"{'='*60}")
    
    from ebooklib import epub
    
    book = epub.read_epub(file_path, {'ignore_ncx': False})
    
    items_list = list(book.get_items())
    
    for item in items_list:
        if item.get_type() == 9:
            name = item.get_name()
            if 'part0008' in name:
                content = item.get_content()
                soup = BeautifulSoup(content, 'html.parser')
                
                print(f"\n【分析文档: {name}】")
                print("-" * 40)
                
                body = soup.find('body')
                if body:
                    body_text = body.get_text(separator='', strip=True)
                    print(f"  body文本长度: {len(body_text)}")
                
                all_tags = {}
                for tag in soup.find_all(True):
                    all_tags[tag.name] = all_tags.get(tag.name, 0) + 1
                
                print(f"  所有标签统计: {all_tags}")
                
                p_tags = soup.find_all('p')
                print(f"\n  前5个<p>标签内容:")
                for i, p in enumerate(p_tags[:5]):
                    text = p.get_text(separator='', strip=True)
                    print(f"    [{i}] {text[:80]}...")
                
                span_tags = soup.find_all('span')
                print(f"\n  前5个<span>标签内容:")
                for i, span in enumerate(span_tags[:5]):
                    text = span.get_text(separator='', strip=True)
                    if text:
                        print(f"    [{i}] class={span.get('class', [])}, text={text[:60]}...")
                
                footnote_elements = soup.find_all(class_=lambda x: x and ('footnote' in x.lower() or 'note' in x.lower()))
                print(f"\n  脚注相关元素 ({len(footnote_elements)} 个):")
                for i, elem in enumerate(footnote_elements[:5]):
                    text = elem.get_text(separator='', strip=True)
                    print(f"    [{i}] class={elem.get('class', [])}, text={text[:60]}...")
                
                break

if __name__ == "__main__":
    test_dir = r"D:\workspace\TraeProjects\booktest"
    
    test_files = [
        "柏拉图哲学作品集（套装6册）.epub",
        "小王子(精排四语插图版).epub",
    ]
    
    for filename in test_files:
        file_path = os.path.join(test_dir, filename)
        if os.path.exists(file_path):
            analyze_epub_ncx(file_path)
            analyze_epub_content_detail(file_path)
