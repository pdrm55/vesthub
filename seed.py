"""
اسکریپت Seed برای پر کردن دیتابیس با داده‌های اولیه.

این اسکریپت برای راه‌اندازی اولیه دیتابیس استفاده می‌شود. وظایف آن شامل:
1. ایجاد تمام جداول دیتابیس بر اساس مدل‌ها.
2. ایجاد نقش‌های کاربری پیش‌فرض (Admin, Investor, Support).
3. ایجاد کاربر ادمین اصلی با استفاده از متغیرهای محیطی.
4. (اختیاری) ایجاد پلن‌های سرمایه‌گذاری و تنظیمات اولیه سیستم.
"""

import os
from app import create_app
from extensions import db
from models import Role, User, InvestmentPlan, SystemSetting
from werkzeug.security import generate_password_hash
from datetime import datetime

# ایجاد یک نمونه از اپلیکیشن برای دسترسی به کانتکست دیتابیس
app = create_app()

def seed_database():
    """تابع اصلی برای اجرای فرآیند seeding."""
    with app.app_context():
        # 1. ایجاد تمام جداول تعریف شده در models.py
        db.create_all()
        print("✅ Database tables created.")

        # ==========================================
        # 2. ایجاد نقش‌ها
        # ==========================================
        roles = {
            'Admin': 'Super Administrator',
            'Investor': 'Standard User',
            'Support': 'Support Agent'
        }
        
        # ایجاد نقش‌ها در صورتی که از قبل وجود نداشته باشند
        for role_name, role_desc in roles.items():
            if not Role.query.filter_by(name=role_name).first():
                permissions = ''
                if role_name == 'Support':
                    permissions = 'manage_tickets,view_users'
                
                new_role = Role(name=role_name, description=role_desc, permissions=permissions)
                db.session.add(new_role)
                print(f"   Role created: {role_name}")
        
        db.session.commit()

        # ==========================================
        # 3. ایجاد ادمین (امن)
        # ==========================================
        # خواندن اطلاعات ادمین از متغیرهای محیطی برای امنیت بیشتر
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
        admin_pass = os.environ.get('ADMIN_PASSWORD')

        # بررسی وجود رمز عبور ادمین در متغیرهای محیطی
        if not admin_pass:
            print("⚠️ هشدار: متغیر ADMIN_PASSWORD تنظیم نشده است. ادمین ساخته نشد.")
        elif not User.query.filter_by(email=admin_email).first():
            admin_role = Role.query.filter_by(name='Admin').first()
            # ایجاد کاربر ادمین با اطلاعات خوانده شده
            admin = User(
                email=admin_email,
                password=generate_password_hash(admin_pass, method='pbkdf2:sha256'),
                first_name='Super',
                last_name='Admin',
                role=admin_role,
                referral_code='ADMIN001',
                is_email_verified=True,
                kyc_status='verified',
                created_at=datetime.utcnow()
            )
            db.session.add(admin)
            print(f"👤 Super Admin created: {admin_email}")
        
        db.session.commit()

        # ==========================================
        # 4. ایجاد پلن‌ها و تنظیمات (مانند قبل)
        # ==========================================
        # این بخش برای ایجاد پلن‌ها و تنظیمات اولیه است. می‌توانید آن را کامل کنید.
        
        # اگر می‌خواهید مطمئن شوید پلن‌ها هستند:
        if not InvestmentPlan.query.first():
             # ... کدهای ساخت پلن ...
             pass

        if not SystemSetting.query.first():
             # ... کدهای تنظیمات ...
             pass
             
        db.session.commit()
        print("\n🎉 Database seeding completed successfully!")

# اجرای تابع seeding اگر اسکریپت مستقیماً اجرا شود
if __name__ == '__main__':
    seed_database()