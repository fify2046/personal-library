# 个人电子书内容提取工具

用于从 PDF/EPUB 电子书中提取内容和图片，构建个人图书系统。

## 环境要求

- Python 3.8+
- PostgreSQL 12+
- Windows/Linux/Mac

## 1. 安装依赖

```bash
cd InitBookData
pip install -r requirements.txt
```

如果 cairosvg 安装失败（Windows），可以跳过 SVG 转换功能：
```bash
pip install PyMuPDF ebooklib psycopg2-binary Pillow beautifulsoup4 lxml
```

## 2. 配置数据库

### 2.1 创建数据库

```bash
psql -U postgres -c "CREATE DATABASE ebook_db;"
```

### 2.2 创建表

```bash
psql -U postgres -d ebook_db -f sql/init_database.sql
psql -U postgres -d ebook_db -f sql/reading_history.sql
psql -U postgres -d ebook_db -f sql/favorites_and_reading_list.sql
psql -U postgres -d ebook_db -f sql/add_display_mode.sql
```

## 3. 运行程序

```bash
python main.py
```

## 4. 使用说明

### 4.1 界面介绍

- **配置区域**: 输入 PostgreSQL 数据库连接信息，点击"测试连接"验证
- **图片目录**: 选择图片保存路径（可选，默认程序目录下 images 文件夹）
- **书籍目录**: 选择存放 PDF/EPUB 文件的根目录（程序会递归扫描子目录）
- **扫描按钮**: 扫描选中目录下的所有 PDF/EPUB 文件
- **开始提取**: 将扫描到的书籍内容提取并存入数据库

### 4.2 操作流程

1. 配置数据库连接信息，点击"测试连接"
2. 选择存放电子书的目录
3. 点击"扫描书籍"扫描目录
4. 查看扫描结果（成功/失败数量）
5. 点击"开始提取"
6. 等待提取完成

## 5. 功能特性

- **PDF 处理**:
  - 使用 PyMuPDF 提取文本
  - 自动识别章节标题
  - 去除强制换行，还原段落
  - 提取嵌入式图片
  - 自动跳过扫描版 PDF

- **EPUB 处理**:
  - 使用 ebooklib 解析
  - 提取原生章节结构
  - 提取所有图片
  - SVG 图片自动转换为 PNG

- **数据存储**:
  - 书籍信息存储
  - 章节结构存储
  - 段落文本存储
  - 图片路径及元信息存储
  - 自动去重（相同文件路径不重复提取）

## 6. 数据库表说明

| 表名 | 说明 |
|------|------|
| books | 书籍信息 |
| chapters | 章节结构 |
| paragraphs | 段落内容 |
| images | 图片信息 |

## 7. 注意事项

- 首次使用请先确保数据库已正确配置
- 图片目录需要有写入权限
- 建议单次处理文件数量不超过 100 本
- 大型 PDF 文件处理可能需要较长时间
