import os
import sys
from ebooklib import epub
from bs4 import BeautifulSoup
import json

def analyze_epub(file_path):
    print(f"\n{'='*60}")
    print(f"分析EPUB文件: {os.path.basename(file_path)}")
    print(f"{'='*60}")
    
    try:
        book = epub.read_epub(file_path, {'ignore_ncx': False})
    except Exception as e:
        print(f"打开EPUB失败: {e}")
        return
    
    print("\n【1. 元数据】")
    for key, values in book.metadata.items():
        print(f"  {key}: {values}")
    
    print("\n【2. 目录结构 (TOC) - 层级分析】")
    print("-" * 40)
    
    def get_toc_hierarchy(toc_items, level=0):
        results = []
        for item in toc_items:
            if hasattr(item, 'title') and hasattr(item, 'href'):
                results.append({
                    'level': level,
                    'title': item.title,
                    'href': item.href
                })
                if hasattr(item, 'children') and item.children:
                    results.extend(get_toc_hierarchy(item.children, level + 1))
        return results
    
    try:
        toc_hierarchy = get_toc_hierarchy(book.toc)
        print(f"  总共 {len(toc_hierarchy)} 个目录项")
        
        level_counts = {}
        for item in toc_hierarchy:
            lvl = item['level']
            level_counts[lvl] = level_counts.get(lvl, 0) + 1
        
        print(f"  层级分布: {level_counts}")
        
        for item in toc_hierarchy[:30]:
            indent = "  " * item['level']
            print(f"{indent}[L{item['level']}] {item['title'][:60]} -> {item['href'][:40]}")
        if len(toc_hierarchy) > 30:
            print(f"  ... 还有 {len(toc_hierarchy) - 30} 项")
            
    except Exception as e:
        print(f"  解析TOC失败: {e}")
    
    print("\n【3. SPINE (阅读顺序)】")
    print("-" * 40)
    spine_items = list(book.spine)
    print(f"  共 {len(spine_items)} 个spine项")
    for idx, item in enumerate(spine_items[:10]):
        print(f"  [{idx}] {item}")
    if len(spine_items) > 10:
        print(f"  ... 还有 {len(spine_items) - 10} 项")
    
    print("\n【4. 所有项目类型统计】")
    print("-" * 40)
    type_counts = {}
    items_list = list(book.get_items())
    for item in items_list:
        item_type = item.get_type()
        type_counts[item_type] = type_counts.get(item_type, 0) + 1
    
    type_names = {
        1: "IMAGE", 2: "STYLE", 3: "SCRIPT", 4: "NAVIGATION",
        5: "VECTOR", 6: "FONT", 7: "VIDEO", 8: "AUDIO",
        9: "TEXT", 10: "UNKNOWN"
    }
    for t, count in sorted(type_counts.items()):
        name = type_names.get(t, f"TYPE_{t}")
        print(f"  {name} (type={t}): {count} 个")

    print("\n【5. 文档项目内容分析】")
    print("-" * 40)
    
    doc_by_name = {}
    for item in items_list:
        if item.get_type() == 9:
            name = item.get_name()
            content = item.get_content()
            soup = BeautifulSoup(content, 'html.parser')
            
            body = soup.find('body')
            if body:
                body_text = body.get_text(separator='', strip=True)
            else:
                body_text = soup.get_text(separator='', strip=True)
            
            p_count = len(soup.find_all('p'))
            div_count = len(soup.find_all('div'))
            span_count = len(soup.find_all('span'))
            img_count = len(soup.find_all('img'))
            h_count = len(soup.find_all(['h1','h2','h3','h4','h5','h6']))
            
            doc_by_name[name] = {
                'body_text': body_text,
                'body_len': len(body_text),
                'p': p_count,
                'div': div_count,
                'span': span_count,
                'img': img_count,
                'h': h_count
            }
    
    sorted_docs = sorted(doc_by_name.items(), key=lambda x: x[1]['body_len'], reverse=True)
    
    print(f"  内容最丰富的10个文档:")
    for name, info in sorted_docs[:10]:
        print(f"    {name[:40]}: {info['body_len']}字符, p={info['p']}, div={info['div']}, span={info['span']}, img={info['img']}")
    
    print("\n【6. 检查潜在内容丢失】")
    print("-" * 40)
    
    for item in items_list:
        if item.get_type() == 9:
            content = item.get_content()
            soup = BeautifulSoup(content, 'html.parser')
            
            body = soup.find('body')
            if body:
                body_text = body.get_text(separator='', strip=True)
            else:
                body_text = soup.get_text(separator='', strip=True)
            
            if len(body_text) > 500:
                current_extract = []
                for tag in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span', 'li', 'blockquote', 'pre', 'td', 'th']):
                    text = tag.get_text(separator='', strip=True)
                    if text:
                        current_extract.append(text)
                extracted_text = ''.join(current_extract)
                
                if len(body_text) > len(extracted_text) + 50:
                    print(f"\n  ⚠️ 可能遗漏内容的文档: {item.get_name()}")
                    print(f"     body文本: {len(body_text)} 字符")
                    print(f"     当前提取: {len(extracted_text)} 字符")
                    print(f"     差异: {len(body_text) - len(extracted_text)} 字符")
                    
                    for tag in soup.find_all(True):
                        if tag.name in ['html', 'head', 'body', 'script', 'style', 'nav', 'footer', 'header']:
                            continue
                        tag_text = tag.get_text(separator='', strip=True)
                        if tag_text and len(tag_text) > 30:
                            current_tags = ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span', 'li', 'blockquote', 'pre', 'td', 'th']
                            if tag.name not in current_tags:
                                print(f"     未处理标签 <{tag.name}>: {tag_text[:50]}...")
                    break

    print("\n【7. 特殊元素检查】")
    print("-" * 40)
    
    for item in items_list:
        if item.get_type() == 9:
            content = item.get_content()
            soup = BeautifulSoup(content, 'html.parser')
            
            footnotes = soup.find_all(class_=lambda x: x and ('footnote' in x.lower() or 'note' in x.lower()))
            if footnotes:
                print(f"  {item.get_name()}: 找到 {len(footnotes)} 个脚注相关元素")
            
            svg_count = len(soup.find_all('svg'))
            if svg_count > 0:
                print(f"  {item.get_name()}: 找到 {len(soup.find_all('svg'))} 个SVG元素")
            
            section_count = len(soup.find_all('section'))
            if section_count > 0:
                print(f"  {item.get_name()}: 找到 {len(soup.find_all('section'))} 个section元素")
                
            article_count = len(soup.find_all('article'))
            if article_count > 0:
                print(f"  {item.get_name()}: 找到 {len(soup.find_all('article'))} 个article元素")

if __name__ == "__main__":
    test_dir = r"D:\workspace\TraeProjects\booktest"
    
    test_files = [
        "柏拉图哲学作品集（套装6册）.epub",
    ]
    
    for filename in test_files:
        file_path = os.path.join(test_dir, filename)
        if os.path.exists(file_path):
            analyze_epub(file_path)
            print("\n")
