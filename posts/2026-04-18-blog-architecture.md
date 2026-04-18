# 我的博客 —— 项目架构全景图

> 基于 Flask + SQLite + Markdown 的轻量级本地博客系统

---

## 一、项目整体定位

```
┌─────────────────────────────────────────────────────────────────┐
│                    myblog  轻量级博客系统                         │
│                                                                 │
│  核心理念：Markdown 文件驱动 + SQLite 持久化                       │
│  运行方式：python app.py  →  http://localhost:5111              │
│  主要特性：                                                      │
│    ✅ 无配置数据库（SQLite 文件即数据库）                          │
│    ✅ 写 .md 文件即发布文章                                       │
│    ✅ 代码高亮（highlight.js CDN）                               │
│    ✅ 响应式移动端适配                                            │
│    ✅ IPv6 双栈支持                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、目录结构总览

```
myblog/
├── app.py              ← 【入口层】Flask 工厂函数，应用启动与配置
├── models.py           ← 【数据层】SQLite 连接管理 + 文章 ORM
├── service.py          ← 【业务层】Markdown 解析 + 文件同步逻辑
├── view.py             ← 【路由层】URL 映射与模板渲染
│
├── templates/          ← 【模板层】Jinja2 HTML 模板继承体系
│   ├── base.html           公共骨架：header / nav / footer / CDN
│   ├── index.html          首页：文章卡片列表
│   └── post.html           详情页：文章全文渲染
│
├── static/             ← 【样式层】全站 CSS
│   └── style.css           约 292 行，含响应式断点
│
├── posts/              ← 【内容源】Markdown 文章目录
│   ├── 2026-03-31-hello.md         第一篇文章：你好，世界！
│   └── 2026-04-01-blog-tech.md    技术说明文章
│
└── blog.db             ← 【数据存储】SQLite 数据库（运行时自动生成）
```

---

## 三、分层架构图

```
┌──────────────────────────────────────────────────────────────┐
│                       用户浏览器                               │
│                   http://localhost:5111                      │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTP 请求
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  【入口层】 app.py                                             │
│                                                              │
│  create_app()                                                │
│  ├── Flask 配置（DATABASE 路径、POSTS_DIR 路径）               │
│  ├── db.init_app(app)          绑定数据库实例                  │
│  ├── register_blueprints(app)  注册路由蓝图                    │
│  ├── @context_processor        注入 current_year 到模板       │
│  ├── @template_filter          format_date 过滤器             │
│  ├── @before_request           每次请求前取出 DB 连接放入 g    │
│  └── 启动时执行：                                              │
│      Post.create_table()  +  post_service.sync_posts()       │
└──────────┬───────────────────────┬───────────────────────────┘
           │                       │
           ▼                       ▼
┌─────────────────┐    ┌────────────────────────────────────────┐
│  【路由层】       │    │  【业务层】 service.py                   │
│  view.py        │    │                                        │
│                 │    │  MarkdownParser                        │
│  GET /          │    │  ├── parse()        提取标题/日期/摘要   │
│  → index()      │    │  └── extract_slug() 从文件名取 slug     │
│  → index.html   │    │                                        │
│                 │    │  PostService                           │
│  GET /post/<slug>    │  ├── sync_posts()   启动时批量同步       │
│  → post()       │    │  ├── _sync_single_post()  单文件处理    │
│  → post.html    │    │  ├── get_all_posts()       查列表       │
│                 │    │  └── get_post_by_slug()    查单篇       │
└────────┬────────┘    └────────────────┬───────────────────────┘
         │                              │
         └──────────────┬───────────────┘
                        │
                        ▼
           ┌────────────────────────────────┐
           │  【数据层】 models.py            │
           │                                │
           │  Database（连接管理）            │
           │  ├── init_app()   绑定 Flask    │
           │  ├── get_db()     取/建连接     │
           │  └── close_db()  请求后关闭     │
           │                                │
           │  Post（文章 ORM，纯类方法）      │
           │  ├── create_table()  建表       │
           │  ├── get_all()       全量查询   │
           │  ├── get_by_slug()   按 slug   │
           │  ├── exists()        存在性检查 │
           │  ├── insert()        插入      │
           │  ├── update()        更新      │
           │  └── upsert()        智能写入  │
           └───────────────┬────────────────┘
                           │
                           ▼
           ┌────────────────────────────────┐
           │  【数据存储】 blog.db            │
           │  SQLite  ·  posts 表            │
           │                                │
           │  id       INTEGER  PK AUTOINCR  │
           │  slug     TEXT     UNIQUE       │
           │  title    TEXT                  │
           │  date     TEXT                  │
           │  summary  TEXT                  │
           │  content  TEXT   (已转 HTML)    │
           │  created_at  TIMESTAMP          │
           └────────────────────────────────┘
```

---

## 四、数据流向图

### 4.1 启动时——文章同步流

```
posts/*.md 文件
     │
     │ os.listdir()
     ▼
MarkdownParser.parse()
     ├── 正则提取 # 一级标题    → title
     ├── 正则提取 date: 元数据  → date（优先）
     ├── 正则提取 summary: 元数据 → summary
     └── 清理元数据行后保留正文
     │
     │ md.convert()（markdown-it + extra/codehilite/tables 扩展）
     ▼
Markdown 文本 → HTML 字符串
     │
     │ Post.upsert()
     ▼
blog.db  posts 表
（slug 存在 → UPDATE；不存在 → INSERT）
```

### 4.2 运行时——HTTP 请求流

```
GET /
  ├── before_request: g.db_conn = db.get_db()
  ├── view.index()
  │     └── post_service.get_all_posts(g.db_conn)
  │           └── Post.get_all()  → SELECT * ORDER BY date DESC
  └── render_template('index.html', posts=posts)
        └── base.html 骨架 + 文章卡片列表

GET /post/<slug>
  ├── before_request: g.db_conn = db.get_db()
  ├── view.post(slug)
  │     └── post_service.get_post_by_slug(g.db_conn, slug)
  │           └── Post.get_by_slug()  → SELECT WHERE slug=?
  └── render_template('post.html', post=post)
        └── base.html 骨架 + {{ post.content | safe }}
              （404.html 兜底：文章不存在时返回 404）
```

---

## 五、模板继承体系

```
base.html（公共骨架）
├── <head>
│     ├── <title> {% block title %} 我的博客 {% endblock %}
│     ├── style.css（本地，Flask url_for）
│     └── highlight.js GitHub 主题（CDN）
├── <header>
│     ├── 网站标题：链接到首页
│     └── 导航：首页
├── <main>
│     └── {% block content %} ← 子模板填充区
├── <footer>
│     └── © {{ current_year }} 我的博客
└── <script> hljs.highlightAll()  代码自动高亮

    ├── index.html（首页）
    │     block title  → "首页 - 我的博客"
    │     block content →
    │       {% for post in posts %}
    │         文章卡片（标题链接、日期、摘要、阅读更多）
    │       {% else %}
    │         空状态提示
    │       {% endfor %}
    │
    └── post.html（详情页）
          block title  → "{{ post.title }} - 我的博客"
          block content →
            文章标题（h1）
            日期（format_date 过滤器）
            {{ post.content | safe }}  ← 直接输出 HTML
            返回首页链接
```

---

## 六、文件依赖关系图

```
app.py
  │  import
  ├──────────────► models.py  (db, Post)
  │  import
  ├──────────────► service.py (post_service)
  │  import
  └──────────────► view.py    (register_blueprints)

view.py
  │  import
  └──────────────► service.py (post_service)

service.py
  │  import
  └──────────────► models.py  (Post, db)

models.py
  │  import
  └──────────────► Flask (g)  ← 无业务依赖，最底层

templates/
  index.html  ──── extends ──► base.html
  post.html   ──── extends ──► base.html
  base.html   ──── link    ──► static/style.css
  base.html   ──── link    ──► highlight.js (CDN)

posts/*.md   ──── 被 service.py 扫描解析
                    ↓
              blog.db (SQLite)
                    ↓
              被 view.py 查询
                    ↓
              被 templates 渲染输出
```

---

## 七、各层职责一览表

| 层次     | 文件                  | 核心职责                                   | 代码量  |
|----------|-----------------------|--------------------------------------------|---------|
| 入口层   | `app.py`              | 工厂函数、配置、过滤器、钩子、启动同步         | 44 行   |
| 路由层   | `view.py`             | URL 映射、蓝图注册、模板渲染、404 处理        | 31 行   |
| 业务层   | `service.py`          | Markdown 解析、文件扫描、Upsert 同步逻辑     | 130 行  |
| 数据层   | `models.py`           | SQLite 连接管理、文章 CRUD 封装              | 119 行  |
| 模板层   | `templates/*.html`    | Jinja2 继承体系、前端结构与变量渲染           | 86 行   |
| 样式层   | `static/style.css`    | 全站样式（卡片布局、代码块、表格、响应式）     | 292 行  |
| 内容源   | `posts/*.md`          | Markdown 格式博客文章（标题/日期/摘要约定）   | 2 篇    |
| 数据存储 | `blog.db`             | SQLite 数据库文件，自动生成                  | -       |

---

## 八、文章 Markdown 格式规范

```markdown
文件名：YYYY-MM-DD-slug.md （如 2026-04-01-my-post.md）

# 文章标题（第一个 # 标题自动作为 title）

<!-- date: 2026-04-18        ← 可选，覆盖文件名中的日期
summary: 这是文章摘要    ← 可选，显示在首页卡片中 -->

正文内容（支持标准 Markdown + 表格/代码高亮/引用扩展）
```

---

## 九、已有文章内容

| 文件名                       | 标题               | 日期       |
|------------------------------|---------------------|------------|
| `2026-03-31-hello.md`        | 你好，世界！         | 2026-03-31 |
| `2026-04-01-blog-tech.md`    | 本地博客系统技术说明 | 2026-04-01 |

---

## 十、后续扩展方向（来自文章内记录）

- [ ] RSS 订阅
- [ ] 标签分类系统
- [ ] 全文搜索功能
- [ ] 文章评论系统
- [ ] 访问统计
