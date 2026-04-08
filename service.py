"""
业务逻辑层
负责文章的解析、同步和处理
"""
import os
import re
from datetime import datetime
import markdown
from models import Post, db


md = markdown.Markdown(extensions=['extra', 'codehilite', 'tables'])


class MarkdownParser:
    """Markdown 解析器"""
    
    # 正则表达式模式
    TITLE_PATTERN = re.compile(r'^#\s+(.+)$', re.MULTILINE)
    DATE_PATTERN = re.compile(r'^date:\s*(.+)$', re.MULTILINE)
    SUMMARY_PATTERN = re.compile(r'^summary:\s*(.+)$', re.MULTILINE)
    
    @classmethod
    def parse(cls, content):
        """解析 Markdown 内容，提取元数据"""
        metadata = {
            'title': None,
            'date': None,
            'summary': None,
            'content': content
        }
        
        # 提取标题（第一个 # 标题）
        title_match = cls.TITLE_PATTERN.search(content)
        if title_match:
            metadata['title'] = title_match.group(1).strip()
            content = re.sub(r'^#\s+.+$', '', content, count=1, flags=re.MULTILINE)
        
        # 提取日期
        date_match = cls.DATE_PATTERN.search(content)
        if date_match:
            metadata['date'] = date_match.group(1).strip()
        
        # 提取摘要
        summary_match = cls.SUMMARY_PATTERN.search(content)
        if summary_match:
            metadata['summary'] = summary_match.group(1).strip()
        
        # 去掉元数据行
        content = re.sub(r'^(date:.*|summary:.*)$\n?', '', content, flags=re.MULTILINE).strip()
        metadata['content'] = content
        return metadata
    
    @classmethod
    def extract_slug(cls, filename):
        """从文件名提取 slug"""
        # 格式: YYYY-MM-DD-slug.md
        parts = filename.replace('.md', '').split('-', 3)
        if len(parts) >= 4:
            return parts[3]
        return filename.replace('.md', '')


class PostService:
    """文章服务类"""
    
    def __init__(self, posts_dir='posts'):
        self.posts_dir = posts_dir
    
    def get_all_posts(self, conn):
        """获取所有文章"""
        return Post.get_all(conn)
    
    def get_post_by_slug(self, conn, slug):
        """根据 slug 获取文章"""
        return Post.get_by_slug(conn, slug)
    
    def sync_posts(self, conn):
        """同步 posts 目录下的文章到数据库"""
        if not os.path.exists(self.posts_dir):
            os.makedirs(self.posts_dir)
            return
        
        for filename in os.listdir(self.posts_dir):
            if not filename.endswith('.md'):
                continue
            
            filepath = os.path.join(self.posts_dir, filename)
            self._sync_single_post(conn, filepath, filename)
        
        conn.commit()
    
    def _sync_single_post(self, conn, filepath, filename):
        """同步单篇文章"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        metadata = MarkdownParser.parse(content)
        slug = MarkdownParser.extract_slug(filename)
        
        # 如果没有从文件中提取到日期，使用文件名中的日期
        if not metadata['date'] and len(filename.split('-')) >= 3:
            date_str = '-'.join(filename.split('-')[:3])
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
                metadata['date'] = date_str
            except ValueError:
                metadata['date'] = datetime.now().strftime('%Y-%m-%d')
        
        # 如果没有标题，使用 slug
        if not metadata['title']:
            metadata['title'] = slug.replace('-', ' ').title()
        
        post_data = {
            'slug': slug,
            'title': metadata['title'],
            'date': metadata['date'] or datetime.now().strftime('%Y-%m-%d'),
            'summary': metadata['summary'] or '',
            'content': md.convert(metadata['content'])
        }
        md.reset()

        if Post.exists(conn, slug):
            Post.update(conn, post_data)
        else:
            Post.insert(conn, post_data)


# 全局服务实例
post_service = PostService()