"""
ماژول وظایف پس‌زمینه (Background Tasks).
شامل توزیع سود روزانه و سیستم بازیابی سودهای عقب‌افتاده.
"""

from datetime import datetime, timedelta, date
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from sqlalchemy import func
from extensions import db

def run_profit_distribution(app):
    """وظیفه توزیع سود روزانه (اجرا توسط Scheduler)."""
    # تغییر استراتژی: استفاده از تابع Backfill برای اطمینان از محاسبه روزهای از قلم افتاده
    # این کار باعث می‌شود حتی اگر اسکریپت چند روز اجرا نشود، در اجرای بعدی همه را جبران کند.
    app.logger.info("--- Scheduler Triggered: Delegating to process_missed_profits ---")
    return process_missed_profits(app)

def process_missed_profits(app):
    """
    سیستم بازیابی و جبران سودهای پرداخت نشده (Backfill).
    """
    with app.app_context():
        from models import Investment, Transaction, SystemSetting
        
        app.logger.info("--- Starting Profit Backfill & Recovery ---")
        
        ref_setting = db.session.get(SystemSetting, 'referral_percentage')
        ref_percent = Decimal(ref_setting.value) if ref_setting else Decimal('2.0')
        
        active_investments = Investment.query.filter_by(status='active').all()
        today = datetime.utcnow().date()
        total_recovered = 0
        
        for inv in active_investments:
            try:
                # قفل کردن رکورد برای جلوگیری از تداخل (اضافه شده برای امنیت بیشتر)
                locked_inv = db.session.query(Investment).filter_by(id=inv.id).with_for_update().first()
                if not locked_inv or locked_inv.status != 'active':
                    db.session.commit()
                    continue

                # تعیین تاریخ شروع بررسی: یک روز بعد از آخرین سود، یا تاریخ شروع سرمایه‌گذاری
                if locked_inv.last_profit_date:
                    current_date = locked_inv.last_profit_date + timedelta(days=1)
                else:
                    current_date = locked_inv.start_date.date()

                # تاریخ سررسید (پایان دوره) — سود فقط تا این تاریخ تعلق می‌گیرد.
                # رکوردهای قدیمی end_date ندارند؛ آن را از روی مدت پلن محاسبه و ذخیره می‌کنیم.
                if locked_inv.end_date:
                    maturity_date = locked_inv.end_date.date()
                else:
                    months = locked_inv.plan.duration_months if locked_inv.plan else 0
                    maturity_dt = locked_inv.start_date + relativedelta(months=months)
                    locked_inv.end_date = maturity_dt
                    maturity_date = maturity_dt.date()
                    db.session.commit()

                # آخرین روزی که سود پرداخت می‌شود: کمینه‌ی «امروز» و «سررسید»
                last_payable_date = min(today, maturity_date)

                # حلقه برای تک تک روزهای عقب افتاده تا پایان دوره
                while current_date <= last_payable_date:
                    # 1. چک کردن اینکه آیا برای این روز خاص قبلاً سود واریز شده؟ (بسیار مهم)
                    existing_tx = Transaction.query.filter(
                        Transaction.investment_id == locked_inv.id,
                        Transaction.type == 'profit',
                        func.date(Transaction.timestamp) == current_date
                    ).first()
                    
                    if existing_tx:
                        # اگر قبلاً واریز شده، برو به روز بعد
                        current_date += timedelta(days=1)
                        continue
                    
                    # 2. محاسبه سود
                    daily_profit = (locked_inv.amount * (locked_inv.plan.annual_return_rate / Decimal('100.0'))) / Decimal('365.0')
                    daily_profit = daily_profit.quantize(Decimal('0.0001'))
                    
                    # تنظیم ساعت واریز به ۱۲ ظهر همان روز تاریخی
                    payout_timestamp = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=12)
                    
                    # 3. ثبت تراکنش
                    user_tx = Transaction(
                        user_id=locked_inv.user_id,
                        investment_id=locked_inv.id,
                        type='profit',
                        amount=daily_profit,
                        description=f"Recovered profit for {current_date}",
                        status='completed',
                        timestamp=payout_timestamp
                    )
                    db.session.add(user_tx)
                    
                    # 4. پاداش معرف
                    if locked_inv.user.referrer_id:
                        bonus = (daily_profit * (ref_percent / Decimal('100.0'))).quantize(Decimal('0.0001'))
                        if bonus > Decimal('0'):
                            ref_tx = Transaction(
                                user_id=locked_inv.user.referrer_id,
                                type='referral_bonus',
                                amount=bonus,
                                description=f"Referral bonus recovery {current_date}",
                                status='completed',
                                timestamp=payout_timestamp
                            )
                            db.session.add(ref_tx)
                    
                    # آپدیت آخرین تاریخ سود
                    if not locked_inv.last_profit_date or current_date > locked_inv.last_profit_date:
                        locked_inv.last_profit_date = current_date
                        
                    db.session.commit()
                    app.logger.info(f"Recovered profit for Investment {locked_inv.id} on {current_date}")
                    total_recovered += 1
                    
                    current_date += timedelta(days=1)
                    
            except Exception as e:
                app.logger.error(f"Error recovering investment {inv.id}: {e}")
                db.session.rollback()
                
        app.logger.info(f"--- Backfill Completed. Total recovered payouts: {total_recovered} ---")
        return total_recovered