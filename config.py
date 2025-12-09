import os
from dotenv import load_dotenv

# بارگذاری متغیرها از فایل .env
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """تنظیمات پایه که در همه محیط‌ها مشترک است"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-fallback-key'
    
    # تنظیمات دیتابیس
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'vesthub.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # تنظیمات ایمیل (اصلاح شده برای محیط واقعی)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') == 'True'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # فرستنده پیش‌فرض (مثلاً: VestHub <noreply@vesthub.org>)
    MAIL_DEFAULT_SENDER = (
        os.environ.get('MAIL_DEFAULT_SENDER_NAME', 'VestHub Security'),
        os.environ.get('MAIL_DEFAULT_SENDER_EMAIL', 'noreply@vesthub.org')
    )

    # تنظیمات آپلود
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # محدودیت ۱۶ مگابایت

    # تنظیمات زبان (جدید)
    LANGUAGES = ['en', 'tr']  # انگلیسی و ترکی

class DevelopmentConfig(Config):
    """تنظیمات محیط توسعه"""
    DEBUG = True

class ProductionConfig(Config):
    """تنظیمات محیط واقعی"""
    DEBUG = False
    # در محیط واقعی، کوکی‌ها باید امن باشند (اگر SSL دارید)
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}