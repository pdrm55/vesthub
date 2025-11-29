"""
ماژول وظایف پس‌زمینه (Background Tasks).

این فایل شامل توابعی است که توسط زمان‌بند (Scheduler) به صورت دوره‌ای
و در پس‌زمینه اجرا می‌شوند. مثال اصلی، وظیفه توزیع سود روزانه است.
"""

from datetime import datetime
from decimal import Decimal
from extensions import db

def run_profit_distribution(app):
    """
    وظیفه توزیع سود روزانه برای سرمایه‌گذاری‌های فعال.

    این تابع توسط APScheduler (معمولاً هر شب در نیمه‌شب) فراخوانی می‌شود.
    این تابع تمام سرمایه‌گذاری‌های فعال را پیدا کرده، سود روزانه آن‌ها را محاسبه
    و به عنوان یک تراکنش 'profit' برای کاربر ثبت می‌کند. همچنین پاداش معرف را نیز محاسبه و ثبت می‌کند.
    """
    with app.app_context():
        from models import Investment, Transaction, SystemSetting, User
        
        print(f"--- Starting Profit Distribution: {datetime.now()} ---")
        
        ref_setting = db.session.get(SystemSetting, 'referral_percentage')
        ref_percent = Decimal(ref_setting.value) if ref_setting else Decimal('2.0')
        
        # دریافت تمام سرمایه‌گذاری‌های فعال
        active_investments = Investment.query.filter_by(status='active').all()
        today = datetime.utcnow().date()
        count = 0
        
        for inv in active_investments:
            if inv.last_profit_date == today: 
                continue

            # محاسبه سود روزانه با استفاده از Decimal برای دقت بالا
            annual_rate = inv.plan.annual_return_rate # Already Decimal from DB
            inv_amount = inv.amount # Already Decimal
            
            # فرمول: (مبلغ سرمایه‌گذاری * (نرخ سود / ۱۰۰)) / ۳۶۵
            daily_profit = (inv_amount * (annual_rate / Decimal('100.0'))) / Decimal('365.0')
            # گرد کردن نتیجه به ۴ رقم اعشار
            daily_profit = daily_profit.quantize(Decimal('0.0001'))
            
            user_tx = Transaction(
                user_id=inv.user_id,
                type='profit',
                amount=daily_profit,
                description=f"Daily profit for plan {inv.plan.name}",
                status='completed',
                timestamp=datetime.utcnow()
            )
            db.session.add(user_tx)
            
            # محاسبه و ثبت پاداش معرف (در صورت وجود)
            if inv.user.referrer_id:
                bonus = (daily_profit * (ref_percent / Decimal('100.0'))).quantize(Decimal('0.0001'))
                if bonus > Decimal('0'):
                    ref_tx = Transaction(
                        user_id=inv.user.referrer_id,
                        type='referral_bonus',
                        amount=bonus,
                        description=f"Referral bonus from ({inv.user.email})",
                        status='completed',
                        timestamp=datetime.utcnow()
                    )
                    db.session.add(ref_tx)
            
            # به‌روزرسانی تاریخ آخرین پرداخت سود برای جلوگیری از پرداخت مجدد در همان روز
            inv.last_profit_date = today
            count += 1
        
        db.session.commit()
        print(f"--- Profit Distribution Completed. Total payouts: {count} ---")
        return count