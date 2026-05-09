# 电子书阅读系统 - 前端

基于 Vue 3 构建的单页应用，提供图书浏览、阅读、AI摘要等功能。

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架（组合式 API）
- **Vue Router** - 路由管理
- **Element Plus** - UI 组件库
- **Axios** - HTTP 客户端
- **Vite** - 构建工具
- **OpenCC** - 简繁体转换
- **marked** - Markdown 渲染

## 目录结构

```
frontend/
├── src/
│   ├── pages/               # 页面组件
│   │   ├── BookList.vue     # 图书列表页（首页）
│   │   ├── BookDetail.vue   # 图书详情页
│   │   ├── Reader.vue       # 阅读器页面
│   │   ├── Manage.vue       # 图书管理页
│   │   ├── Favorites.vue    # 收藏列表页
│   │   ├── History.vue      # 阅读历史页
│   │   ├── ReadingList.vue  # 阅读列表页
│   │   └── SystemConfig.vue # 系统配置页（AI模型、提示词模板等）
│   ├── utils/               # 工具模块
│   │   └── api.js          # API 请求封装
│   ├── App.vue              # 根组件
│   └── main.js              # 应用入口
├── index.html               # HTML 入口
├── package.json             # 依赖配置
└── vite.config.js           # Vite 配置
```

## 页面说明

### BookList.vue - 图书列表页
- 图书搜索（书名、作者、内容）
- 筛选功能（全部/PDF/EPUB）
- 排序功能（最近添加/书名排序）
- 收藏和阅读列表入口

### BookDetail.vue - 图书详情页
- 图书信息展示
- 评分功能
- 阅读/继续阅读
- AI 摘要生成（支持选择模板）

### Reader.vue - 阅读器
- 章节导航（支持展开/收缩）
- 字体大小/行间距调整
- 简繁切换
- 暗色模式
- AI 摘要面板（支持模板选择、位置切换）
- 快捷键支持：
  - `←` / `→` - 切换章节
  - `Ctrl` + `+` / `Ctrl` + `-` - 调整字体大小

### SystemConfig.vue - 系统配置页
- AI 功能开关
- AI 模型配置（支持多个模型）
- 模型参数配置（温度、最大token、超时、限速）
- AI 提示词模板管理

## 本地存储

系统使用 `localStorage` 保存以下用户偏好设置：
- `fontSize` - 字体大小
- `lineHeight` - 行间距
- `isDarkMode` - 暗色模式
- `searchKeyword` - 搜索关键词
- `booksPerPage` - 每页显示数量
- `sortOrder` - 排序方式
- `displayMode` - 显示方式（图标/列表）
- `ai_settings` - AI 设置（模板名称、摘要位置）

## 启动方式

```bash
cd frontend
npm install
npm run dev
```

访问地址：`http://localhost:5173`

## API 代理

开发环境下，Vite 配置了 `/api` 到 `http://localhost:8000/api` 的代理。

## 路由配置

| 路径 | 页面 | 描述 |
|------|------|------|
| `/` | BookList | 图书列表 |
| `/book/:id` | BookDetail | 图书详情 |
| `/read/:bookId/:chapterId?` | Reader | 阅读器 |
| `/manage` | Manage | 图书管理 |
| `/favorites` | Favorites | 收藏列表 |
| `/reading` | ReadingList | 阅读列表 |
| `/history` | History | 阅读历史 |
| `/config` | SystemConfig | 系统配置 |
