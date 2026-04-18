import os
from datetime import datetime
from flask import Flask, g
from models import db, Post
from service import post_service
from view import register_blueprints


def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config['DATABASE'] = os.path.join(app.root_path, 'blog.db')
    app.config['POSTS_DIR'] = os.path.join(app.root_path, 'posts')
    app.config['SECRET_KEY'] = 'myblog-secret-key-2026'

    db.init_app(app)
    register_blueprints(app)

    @app.context_processor
    def inject_current_year():
        return dict(current_year=datetime.now().year)

    @app.template_filter('format_date')
    def format_date(date_str):
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.strftime('%Y年%m月%d日')
        except Exception:
            return date_str

    @app.before_request
    def before_request():
        g.db_conn = db.get_db()

    with app.app_context():
        connection = db.get_db()
        Post.create_table(connection)
        post_service.sync_posts(connection)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='::', port=5111)
