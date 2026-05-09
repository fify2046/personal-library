# 电子书阅读系统 - 后端

基于 FastAPI 构建的 RESTful API 后端服务，为前端提供图书管理、阅读、AI摘要等功能接口。

## 技术栈

- **Python 3.9+**
- **FastAPI** - Web 框架
- **SQLAlchemy** - ORM 工具
- **PostgreSQL** - 数据库（版本 17）
- **Uvicorn** - ASGI 服务器

## 目录结构

```
backend/
├── ai/                    # AI 模型调用模块
│   ├── __init__.py
│   └── base.py           # AI 服务基类和实现（OpenAI、Anthropic等）
├── api/                   # API 路由模块
│   ├── __init__.py
│   ├── ai_summary.py      # AI 摘要生成接口
│   ├── books.py           # 图书管理接口
│   ├── chapters.py        # 章节内容接口
│   ├── favorites.py       # 收藏功能接口
│   ├── images.py          # 图片访问接口
│   ├── reading.py         # 阅读进度接口
│   ├── reading_list.py    # 阅读列表接口
│   └── system_config.py   # 系统配置接口（AI模型、提示词模板等）
├── config/                # 配置管理
│   ├── config_manager.py  # 配置管理器
│   └── system_config.example.json  # 配置示例文件
├── db/                    # 数据库模块
│   ├── config.py          # 数据库配置
│   ├── database.py        # 数据库连接
│   └── models.py          # SQLAlchemy 模型定义
├── main.py                # 应用入口
└── requirements.txt       # Python 依赖
```

## API 接口列表

### 图书相关
| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/books` | GET | 获取图书列表（支持分页、筛选、搜索） |
| `/api/books/{book_id}` | GET | 获取图书详情 |
| `/api/books/{book_id}/chapters` | GET | 获取图书章节列表 |
| `/api/books/{book_id}/display_mode` | GET/PUT | 获取/设置简繁显示模式 |

### 章节内容
| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/chapters/{chapter_id}/content` | GET | 获取章节内容（段落+图片） |
| `/api/images/{image_path}` | GET | 获取图片文件 |

### 阅读功能
| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/reading/progress` | POST | 保存阅读进度 |
| `/api/reading/progress/{book_id}` | GET | 获取阅读进度 |
| `/api/reading/history` | GET | 获取阅读历史 |

### 收藏与列表
| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/favorites/*` | - | 收藏相关接口 |
| `/api/reading_list/*` | - | 阅读列表接口 |

### AI 功能
| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/ai/status` | GET | 获取 AI 功能状态 |
| `/api/ai/summary/{chapter_id}` | GET | 获取章节 AI 摘要 |
| `/api/ai/summary/generate` | POST | 生成 AI 摘要 |

### 系统配置
| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/config` | GET | 获取系统配置 |
| `/api/config/prompt-templates` | GET/POST | 获取/添加提示词模板 |
| `/api/config/prompt-templates/{name}` | PUT/DELETE | 更新/删除模板 |

## 配置说明

### 环境变量 (.env)

```env
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/ebook_db
```

### 系统配置 (config/system_config.json)

配置文件包含以下配置项：
- `ai_enabled` - AI 功能开关
- `default_model` - 默认 AI 模型
- `min_content_length` - 生成摘要的最小内容长度
- `models` - AI 模型列表（包含 API密钥、参数、限速设置等）
- `prompts` - 默认提示词模板
- `prompt_templates` - 自定义提示词模板列表

## 启动方式

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API 文档访问地址：`http://localhost:8000/docs`

## 数据库说明

数据库表结构定义在 `../InitBookData/sql/init_database.sql` 文件中。

数据库修改时请更新该 SQL 文件，不要在此目录创建迁移脚本。
