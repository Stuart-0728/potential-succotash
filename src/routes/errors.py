from flask import render_template, current_app, request
import logging

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    @app.errorhandler(404)
    def page_not_found(e):
        logger.warning(f"404 错误: {request.path}")
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error(f"500 错误: {e}")
        return render_template('500.html'), 500

    @app.errorhandler(403)
    def forbidden(e):
        logger.warning(f"403 错误: {request.path}")
        return render_template('404.html'), 403  # 使用相同的模板，但状态码不同

    @app.errorhandler(400)
    def bad_request(e):
        logger.warning(f"400 错误: {request.path}")
        return render_template('404.html'), 400  # 使用相同的模板，但状态码不同 