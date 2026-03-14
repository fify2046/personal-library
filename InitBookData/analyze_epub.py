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
    
    print("\n【2. 目录结构 (TOC)】")
    print("-" * 40)
    
    def print_toc(toc_items, level=0):
        indent = "  " * level
        for item in toc_items:
            if hasattr(item, 'title') and hasattr(item, 'href'):
                print(f"{indent}[{level}] {item.title} -> {item.href}")
                if hasattr(item, 'children') and item.children:
                    print_toc(item.children, level + 1)
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                title = item[0] if isinstance(item[0], str) else str(item[0])
                href = item[1] if len(item) > 1 else ""
                print(f"{indent}[{level}] {title} -> {href}")
                if len(item) > 2:
                    children = item[2] if isinstance(item[2], (list, tuple)) else []
                    print_toc(children, level + 1)
            elif isinstance(item, str):
                print(f"{indent}[{level}] {item}")
    
    try:
        print_toc(book.toc)
    except Exception as e:
        print(f"  解析TOC失败: {e}")
    
    print("\n【3. SPINE (阅读顺序)】")
    print("-" * 40)
    spine_items = list(book.spine)
    print(f"  共 {len(spine_items)} 个spine项")
    for idx, item in enumerate(spine_items[:20]):
        print(f"  [{idx}] {item}")
    if len(spine_items) > 20:
        print(f"  ... 还有 {len(spine_items) - 20} 项")
    
    print("\n【4. 所有项目类型统计】")
    print("-" * 40)
    type_counts = {}
    items_list = list(book.get_items())
    for item in items_list:
        item_type = item.get_type()
        type_counts[item_type] = type_counts.get(item_type, 0) + 1
    
    type_names = {
        1: "IMAGE",
        2: "STYLE", 
        3: "SCRIPT",
        4: "NAVIGATION",
        5: "VECTOR",
        6: "FONT",
        7: "VIDEO",
        8: "AUDIO",
        9: "TEXT",
        10: "UNKNOWN"
    }
    for t, count in sorted(type_counts.items()):
        name = type_names.get(t, f"TYPE_{t}")
        print(f"  {name} (type={t}): {count} 个")
    
    print("\n【5. 文档项目详情】")
    print("-" * 40)
    doc_count = 0
    for item in items_list:
        if item.get_type() == 9:
            doc_count += 1
            name = item.get_name()
            content = item.get_content()
            soup = BeautifulSoup(content, 'html.parser')
            
            text_len = len(soup.get_text().strip())
            h_tags = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            p_tags = soup.find_all('p')
            img_tags = soup.find_all('img')
            div_tags = soup.find_all('div')
            
            h_titles = [h.get_text().strip()[:50] for h in h_tags[:3] if h.get_text().strip()]
            
            print(f"\n  [{doc_count}] {name}")
            print(f"      文本长度: {text_len}, 标题: {h_titles}")
            print(f"      标签统计: p={len(p_tags)}, div={len(div_tags)}, img={len(img_tags)}, h={len(h_tags)}")
            
            if doc_count >= 10:
                print(f"\n  ... 还有 {sum(1 for i in items_list if i.get_type() == 9) - 10} 个文档")
                break
    
    print("\n【6. NCX/NAV导航文件】")
    print("-" * 40)
    for item in items_list:
        if item.get_type() == 4 or 'nav' in item.get_name().lower() or 'ncx' in item.get_name().lower():
            print(f"\n  导航文件: {item.get_name()}")
            content = item.get_content()
            if content:
                soup = BeautifulSoup(content, 'xml' if 'ncx' in item.get_name().lower() else 'html.parser')
                
                nav_points = soup.find_all('navPoint')
                if nav_points:
                    print(f"  NCX格式, 找到 {len(nav_points)} 个navPoint")
                    for np in nav_points[:10]:
                        text = np.find('text')
                        content_tag = np.find('content')
                        if text and content_tag:
                            src = content_tag.get('src', '')
                            print(f"    - {text.get_text()[:50]} -> {src[:50]}")
                
                nav_li = soup.find_all('li')
                if nav_li and not nav_points:
                    print(f"  NAV格式, 找到 {len(nav_li)} 个li项")
                    for li in nav_li[:10]:
                        a = li.find('a')
                        if a:
                            print(f"    - {a.get_text()[:50]} -> {a.get('href', '')[:50]}")

    print("\n【7. 内容提取测试】")
    print("-" * 40)
    for item in items_list:
        if item.get_type() == 9:
            content = item.get_content()
            soup = BeautifulSoup(content, 'html.parser')
            
            all_text_elements = soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                                               'span', 'li', 'blockquote', 'pre', 'td', 'th'])
            all_text = ' '.join([e.get_text().strip() for e in all_text_elements])
            
            body = soup.find('body')
            if body:
                body_text = body.get_text().strip()
            else:
                body_text = soup.get_text().strip()
            
            if len(body_text) > 100:
                print(f"\n  文档: {item.get_name()}")
                print(f"  body文本长度: {len(body_text)}")
                print(f"  提取元素文本长度: {len(all_text)}")
                print(f"  差异: {len(body_text) - len(all_text)} 字符")
                
                if len(body_text) > len(all_text) + 100:
                    print(f"  ⚠️ 可能遗漏内容!")
                    
                    for tag in soup.find_all(True):
                        tag_text = tag.get_text().strip()
                        if tag_text and tag.name not in ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                                                          'span', 'li', 'blockquote', 'pre', 'td', 'th',
                                                          'html', 'head', 'body', 'script', 'style']:
                            if len(tag_text) > 20:
                                print(f"    未处理标签: <{tag.name}> 内容: {tag_text[:50]}...")
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
            analyze_epub(file_path)
            print("\n")
