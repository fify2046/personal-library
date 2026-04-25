# 电子书数据提取工具

用于从 PDF 和 EPUB 电子书中提取内容（章节、段落、图片）并保存到 PostgreSQL 数据库。

## 快速开始

```bash
# Windows 双击运行
start.bat

# 或手动启动
pip install -r requirements.txt
python main.py
```

## 配置

首次使用将 `settings.json.example` 复制为 `settings.json` 并填入数据库连接信息：

```bash
cp settings.json.example settings.json
```

```json
{
  "database": {
    "host": "localhost",
    "port": 5432,
    "database": "ebook_db",
    "user": "your_username",
    "password": "your_password"
  },
  "paths": {
    "images_dir": "./images"
  }
}
```

## 数据库初始化

```bash
psql -U postgres -d ebook_db -f sql/init_database.sql
```

## 技术栈

- **PyMuPDF (fitz)** - PDF 处理
- **EbookLib** - EPUB 处理
- **BeautifulSoup / lxml** - HTML/XML 解析
- **Pillow / cairosvg** - 图片处理（含 SVG 转 PNG）
- **psycopg2** - PostgreSQL 连接池

## 核心模块

| 模块 | 说明 |
|------|------|
| `main.py` | Tkinter GUI 入口 |
| `db.py` | DatabaseManager 单例，连接池管理 |
| `pdf_extractor.py` | PDF 提取，自动检测扫描版并跳过 |
| `epub_extractor.py` | EPUB 提取，支持 NCX/EPUB3 导航、分片文件、多线程 |
| `image_processor.py` | 图片保存、SVG 转换、封面提取 |

## 注意事项

- `settings.json` 包含数据库密码，已加入 `.gitignore`
- 数据库表结构变更后需同步更新 `sql/init_database.sql`
