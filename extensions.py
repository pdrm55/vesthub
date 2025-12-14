"""
ماژول متمرکزسازی افزونه‌های Flask.

در این فایل، تمام نمونه‌های افزونه‌های مورد استفاده در پروژه (مانند SQLAlchemy, LoginManager)
به صورت unbound (متصل نشده به اپلیکیشن) ایجاد می‌شوند. این الگو به ما اجازه می‌دهد
تا از این نمونه‌ها در بخش‌های مختلف پروژه (مانند مدل‌ها و بلوپرینت‌ها) قبل از
ایجاد نمونه اصلی اپلیکیشن در app.py استفاده کنیم و از خطاهای circular import جلوگیری کنیم.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler
from flask_wtf.csrf import CSRFProtect
from flask_babel import Babel
from authlib.integrations.flask_client import OAuth


# ایجاد نمونه‌های افزونه‌ها به صورت متصل نشده (unbound)
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
scheduler = BackgroundScheduler()
csrf = CSRFProtect()
babel = Babel()
oauth = OAuth()

# تنظیمات مربوط به مدیریت ورود کاربران
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'