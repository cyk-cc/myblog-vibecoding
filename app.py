import os
import re
import sqlite3
from datetime import datetime
from flask import Flask, render_template, g, abort
import markdown

app = Flask(__name__)
app.config['DATABASE'] = os.path.join(app.root_path, 'blog.db')
app.config['POSTS_DIR'] = os.path.join(app.root_path, 'posts')

# 添加模板全局变量 current_year
@app.context_processor
def inject_current_year():
    return dict(current_year=datetime.now().year)

# Markdown 转换器
md = markdown.Markdown(extensions=['extra', 'codehilite', 'toc', 'tables'])

def get_db():
    """获取数据库连接"""
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """初始化数据库"""
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            summary TEXT,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db.commit()

def parse_markdown_file(filepath):
    """解析 Markdown 文件，提取元数据和内容"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取文件名中的日期和 slug
    filename = os.path.basename(filepath)
    match = re.match(r'(\d{4}-\d{2}-\d{2})-(.+)\.md', filename)
    if not match:
        return None
    
    date_str, slug = match.groups()
    
    # 解析 Markdown 内容
    # 查找第一个标题作为文章标题
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1) if title_match else slug.replace('-', ' ').title()
    
    # 生成摘要（前200个字符）
    plain_text = re.sub(r'[#*`\[\]\(\)]', '', content)
    summary = plain_text[:200] + '...' if len(plain_text) > 200 else plain_text
    
    # 转换 Markdown 为 HTML
    html_content = md.convert(content)
    md.reset()
    
    return {
        'slug': slug,
        'title': title,
        'date': date_str,
        'summary': summary,
        'content': html_content
    }

def load_posts():
    """从 Markdown 文件加载文章到数据库"""
    db = get_db()
    posts_dir = app.config['POSTS_DIR']
    
    if not os.path.exists(posts_dir):
        return
    
    for filename in os.listdir(posts_dir):
        if filename.endswith('.md'):
            filepath = os.path.join(posts_dir, filename)
            post = parse_markdown_file(filepath)
            if post:
                # 检查文章是否已存在
                existing = db.execute(
                    'SELECT id FROM posts WHERE slug = ?', (post['slug'],)
                ).fetchone()
                
                if existing:
                    # 更新现有文章
                    db.execute('''
                        UPDATE posts 
                        SET title = ?, date = ?, summary = ?, content = ?
                        WHERE slug = ?
                    ''', (post['title'], post['date'], post['summary'], 
                          post['content'], post['slug']))
                else:
                    # 插入新文章
                    db.execute('''
                        INSERT INTO posts (slug, title, date, summary, content)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (post['slug'], post['title'], post['date'], 
                          post['summary'], post['content']))
    
    db.commit()

@app.route('/')
def index():
    """首页 - 显示文章列表"""
    db = get_db()
    posts = db.execute(
        'SELECT * FROM posts ORDER BY date DESC'
    ).fetchall()
    return render_template('index.html', posts=posts)

@app.route('/post/<slug>')
def post(slug):
    """文章详情页"""
    db = get_db()
    post = db.execute(
        'SELECT * FROM posts WHERE slug = ?', (slug,)
    ).fetchone()
    
    if post is None:
        abort(404)
    
    return render_template('post.html', post=post)

@app.template_filter('format_date')
def format_date(date_str):
    """格式化日期"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%Y年%m月%d日')
    except:
        return date_str

if __name__ == '__main__':
    with app.app_context():
        init_db()
        load_posts()
    app.run(debug=True, host='::', port=5111)   # 启用 IPv6