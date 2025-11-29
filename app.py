"""
فایل اصلی اپلیکیشن و پیاده‌سازی الگوی Application Factory.

این فایل شامل تابع `create_app` است که مسئولیت ایجاد و پیکربندی
نمونه اصلی اپلیکیشن Flask را بر عهده دارد. این الگو به ما اجازه می‌دهد
تا نمونه‌های مختلفی از اپلیکیشن با تنظیمات متفاوت (مثلاً برای توسعه، تست یا پروداکشن) ایجاد کنیم.
"""

import os
import atexit
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template
from flask_wtf.csrf import CSRFError
from config import config
from extensions import db, login_manager, mail, scheduler, csrf
from tasks import run_profit_distribution
from utils import has_permission

from routes.auth import auth_bp
from routes.main import main_bp
from routes.user import user_bp
from routes.admin import admin_bp

def create_app(config_name='default'):
    """
    ایجاد و پیکربندی یک نمونه از اپلیکیشن Flask.

    Args:
        config_name (str): نام تنظیمات مورد نظر (مثلاً 'development' یا 'production').

    Returns:
        Flask: یک نمونه پیکربندی شده از اپلیکیشن Flask.
    """
    app = Flask(__name__)
    
    # 1. بارگذاری تنظیمات از آبجکت کانفیگ
    app.config.from_object(config[config_name])
    
    # 2. راه‌اندازی و اتصال افزونه‌ها به اپلیکیشن
    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # 3. ثبت بلوپرینت‌ها برای ماژولار کردن مسیرها (routes)
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    
    # 4. افزودن توابع کاربردی به کانتکست Jinja2
    # این تابع باعث می‌شود `has_permission` در تمام تمپلیت‌ها قابل دسترس باشد.
    @app.context_processor
    def inject_utilities():
        return dict(has_permission=has_permission)

    # 5. تنظیم user_loader برای Flask-Login
    # این تابع به Flask-Login می‌گوید چگونه کاربر را بر اساس ID از دیتابیس بارگذاری کند.
    from models import User
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # --- 6. ثبت کنترل‌کننده‌های خطا (Error Handlers) ---
    
    # کنترل‌کننده برای خطای 404 (صفحه پیدا نشد)
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('base.html', content="<h3>404 - Page Not Found</h3><p>The page you are looking for does not exist.</p>"), 404

    # کنترل‌کننده برای خطای CSRF
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return render_template('base.html', content=f"<h3>Security Error (400)</h3><p>{e.description}</p>"), 400

    # کنترل‌کننده برای خطای 500 (خطای داخلی سرور)
    @app.errorhandler(500)
    def internal_server_error(e):
        # ثبت جزئیات خطا در فایل لاگ برای عیب‌یابی در آینده
        app.logger.error(f'Server Error: {e}')
        return render_template('base.html', content="<h3>Internal Server Error (500)</h3><p>We are experiencing technical difficulties. Please try again later.</p>"), 500

    # 7. تنظیمات لاگ‌گیری برای محیط Production
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/vesthub.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('VestHub startup')

    # 8. راه‌اندازی زمان‌بند (Scheduler) برای اجرای وظایف پس‌زمینه
    # شرط `os.environ.get('WERKZEUG_RUN_MAIN') == 'true'` از اجرای دوباره زمان‌بند در حالت دیباگ جلوگیری می‌کند.
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        if not scheduler.running:
            scheduler.add_job(
                func=lambda: run_profit_distribution(app), 
                trigger="cron", 
                hour=0, 
                minute=0,
                id='profit_distribution_job',
                replace_existing=True
            )
            scheduler.start()
            # ثبت یک تابع برای خاموش کردن زمان‌بند هنگام خروج از اپلیکیشن
            atexit.register(lambda: scheduler.shutdown())

    return app

# اجرای اپلیکیشن در حالت توسعه اگر فایل مستقیماً اجرا شود
if __name__ == '__main__':
    app = create_app('development')
    app.run(debug=True, host='0.0.0.0', port=5000)