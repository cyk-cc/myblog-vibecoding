"""
路由与视图层
使用蓝图组织路由
"""
from flask import Blueprint, render_template, g
from service import post_service


# 创建蓝图
blog_bp = Blueprint('blog', __name__)


@blog_bp.route('/')
def index():
    """首页 - 显示文章列表"""
    posts = post_service.get_all_posts(g.db_conn)
    return render_template('index.html', posts=posts)


@blog_bp.route('/post/<slug>')
def post(slug):
    """文章详情页"""
    post = post_service.get_post_by_slug(g.db_conn, slug)
    if post is None:
        return render_template('404.html'), 404
    return render_template('post.html', post=post)


def register_blueprints(app):
    """注册蓝图到 Flask 应用"""
    app.register_blueprint(blog_bp)