"""
路由与视图层
使用蓝图组织路由
"""
import os
from datetime import datetime
from flask import Blueprint, render_template, g, request, redirect, url_for, flash, current_app
from service import post_service
from models import Post


# 创建蓝图
blog_bp = Blueprint('blog', __name__)

ALLOWED_EXTENSIONS = {'md'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
    # 每次访问阅读量 +1
    Post.increment_views(g.db_conn, slug)
    # 重新获取最新数据（含更新后的 views）
    post = post_service.get_post_by_slug(g.db_conn, slug)
    return render_template('post.html', post=post)


@blog_bp.route('/stats')
def stats():
    """全站访问统计页"""
    data = Post.get_site_stats(g.db_conn)
    return render_template('stats.html', **data)


@blog_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    """文件上传页"""
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('请选择要上传的 Markdown 文件', 'error')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('只支持 .md 格式的文件', 'error')
            return redirect(request.url)

        # 生成新文件名：上传时间 + 原文件名
        original_name = file.filename  # e.g. hello-world.md
        upload_time = datetime.now().strftime('%Y-%m-%d')
        # 去掉原文件名中已有的 YYYY-MM-DD- 前缀，避免重复
        name_without_ext = original_name.rsplit('.', 1)[0]
        parts = name_without_ext.split('-')
        if len(parts) >= 3:
            try:
                datetime.strptime('-'.join(parts[:3]), '%Y-%m-%d')
                # 原文件名已有日期前缀，去掉它
                slug_part = '-'.join(parts[3:]) if len(parts) > 3 else name_without_ext
            except ValueError:
                slug_part = name_without_ext
        else:
            slug_part = name_without_ext

        new_filename = f'{upload_time}-{slug_part}.md'
        posts_dir = current_app.config['POSTS_DIR']
        save_path = os.path.join(posts_dir, new_filename)

        # 若同名文件已存在，加时间戳后缀区分
        if os.path.exists(save_path):
            ts = datetime.now().strftime('%H%M%S')
            new_filename = f'{upload_time}-{slug_part}-{ts}.md'
            save_path = os.path.join(posts_dir, new_filename)

        file.save(save_path)

        # 立即同步新文章到数据库
        post_service._sync_single_post(g.db_conn, save_path, new_filename)
        g.db_conn.commit()

        flash(f'上传成功！文件已保存为 {new_filename}', 'success')
        return redirect(url_for('blog.index'))

    return render_template('upload.html')


def register_blueprints(app):
    """注册蓝图到 Flask 应用"""
    app.register_blueprint(blog_bp)