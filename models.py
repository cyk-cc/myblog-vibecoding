"""
数据库模型层
负责数据库连接管理和数据模型定义
"""
import os
import sqlite3
from flask import g


class Database:
    """数据库管理类"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化数据库配置"""
        self.app = app
        app.config.setdefault('DATABASE', os.path.join(app.root_path, 'blog.db'))
        app.teardown_appcontext(self.close_db)
    
    def get_db(self):
        """获取数据库连接"""
        if 'db' not in g:
            g.db = sqlite3.connect(self.app.config['DATABASE'])
            g.db.row_factory = sqlite3.Row
        return g.db
    
    def close_db(self, e=None):
        """关闭数据库连接"""
        db = g.pop('db', None)
        if db is not None:
            db.close()


# 全局数据库实例
db = Database()


class Post:
    """文章模型类"""
    
    TABLE_NAME = 'posts'
    
    @classmethod
    def create_table(cls, connection):
        """创建文章表，并自动迁移旧表添加 views 字段"""
        connection.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                summary TEXT,
                content TEXT NOT NULL,
                views INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # 兼容旧表：若 views 列不存在则补充添加
        cols = [row[1] for row in connection.execute('PRAGMA table_info(posts)').fetchall()]
        if 'views' not in cols:
            connection.execute('ALTER TABLE posts ADD COLUMN views INTEGER NOT NULL DEFAULT 0')
        connection.commit()
    
    @classmethod
    def get_all(cls, connection):
        """获取所有文章（按日期降序）"""
        return connection.execute(
            f'SELECT * FROM {cls.TABLE_NAME} ORDER BY date DESC'
        ).fetchall()
    
    @classmethod
    def get_by_slug(cls, connection, slug):
        """根据 slug 获取文章"""
        return connection.execute(
            f'SELECT * FROM {cls.TABLE_NAME} WHERE slug = ?', (slug,)
        ).fetchone()
    
    @classmethod
    def exists(cls, connection, slug):
        """检查文章是否存在"""
        return connection.execute(
            f'SELECT id FROM {cls.TABLE_NAME} WHERE slug = ?', (slug,)
        ).fetchone() is not None
    
    @classmethod
    def insert(cls, connection, post_data):
        """插入新文章"""
        connection.execute('''
            INSERT INTO posts (slug, title, date, summary, content)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            post_data['slug'],
            post_data['title'],
            post_data['date'],
            post_data['summary'],
            post_data['content']
        ))
    
    @classmethod
    def update(cls, connection, post_data):
        """更新文章（不重置阅读量）"""
        connection.execute('''
            UPDATE posts 
            SET title = ?, date = ?, summary = ?, content = ?
            WHERE slug = ?
        ''', (
            post_data['title'],
            post_data['date'],
            post_data['summary'],
            post_data['content'],
            post_data['slug']
        ))
    
    @classmethod
    def upsert(cls, connection, post_data):
        """插入或更新文章"""
        if cls.exists(connection, post_data['slug']):
            cls.update(connection, post_data)
        else:
            cls.insert(connection, post_data)

    @classmethod
    def increment_views(cls, connection, slug):
        """文章阅读量 +1"""
        connection.execute(
            f'UPDATE {cls.TABLE_NAME} SET views = views + 1 WHERE slug = ?', (slug,)
        )
        connection.commit()

    @classmethod
    def get_site_stats(cls, connection):
        """获取全站统计数据"""
        total_posts = connection.execute(
            f'SELECT COUNT(*) as cnt FROM {cls.TABLE_NAME}'
        ).fetchone()['cnt']
        total_views = connection.execute(
            f'SELECT COALESCE(SUM(views), 0) as total FROM {cls.TABLE_NAME}'
        ).fetchone()['total']
        top_posts = connection.execute(
            f'SELECT slug, title, views, date FROM {cls.TABLE_NAME} ORDER BY views DESC LIMIT 10'
        ).fetchall()
        return {
            'total_posts': total_posts,
            'total_views': total_views,
            'top_posts': top_posts,
        }