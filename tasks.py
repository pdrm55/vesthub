"""
ماژول وظایف پس‌زمینه (Background Tasks).
شامل توزیع سود روزانه و سیستم بازیابی سودهای عقب‌افتاده.
"""

import logging
from datetime import datetime, timedelta, date
from decimal import Decimal
from sqlalchemy import func
from extensions import db

# تنظیم لاگر
logger = logging.getLogger(__name__)

def run_profit_distribution(app):
    """وظیفه توزیع سود روزانه (اجرا توسط Scheduler)."""
    with app.app_context():
        from models import Investment, Transaction, SystemSetting
        
        logger.info(f"--- Starting Profit Distribution: {datetime.now()} ---")
        
        ref_setting = db.session.get(SystemSetting, 'referral_percentage')
        ref_percent = Decimal(ref_setting.value) if ref_setting else Decimal('2.0')
        
        active_investments = Investment.query.filter_by(status='active').all()
        today = datetime.utcnow().date()
        count = 0
        
        for inv in active_investments:
            try:
                # قفل کردن رکورد
                locked_inv = db.session.query(Investment).filter_by(id=inv.id).with_for_update().first()
                if not locked_inv: continue

                # جلوگیری از پرداخت تکراری در همان روز
                if locked_inv.last_profit_date == today:
                    db.session.commit()
                    continue

                annual_rate = locked_inv.plan.annual_return_rate
                daily_profit = (locked_inv.amount * (annual_rate / Decimal('100.0'))) / Decimal('365.0')
                daily_profit = daily_profit.quantize(Decimal('0.0001'))
                
                user_tx = Transaction(
                    user_id=locked_inv.user_id,
                    investment_id=locked_inv.id,
                    type='profit',
                    amount=daily_profit,
                    description=f"Daily profit for plan {locked_inv.plan.name}",
                    status='completed',
                    timestamp=datetime.utcnow()
                )
                db.session.add(user_tx)
                
                # پاداش معرف
                if locked_inv.user.referrer_id:
                    bonus = (daily_profit * (ref_percent / Decimal('100.0'))).quantize(Decimal('0.0001'))
                    if bonus > Decimal('0'):
                        ref_tx = Transaction(
                            user_id=locked_inv.user.referrer_id,
                            type='referral_bonus',
                            amount=bonus,
                            description=f"Referral bonus from ({locked_inv.user.email})",
                            status='completed',
                            timestamp=datetime.utcnow()
                        )
                        db.session.add(ref_tx)
                
                locked_inv.last_profit_date = today
                db.session.commit()
                count += 1
            except Exception as e:
                logger.error(f"Error processing investment {inv.id}: {e}")
                db.session.rollback()
        
        logger.info(f"--- Profit Distribution Completed. Total payouts: {count} ---")
        return count

def process_missed_profits(app):
    """
    سیستم بازیابی و جبران سودهای پرداخت نشده (Backfill).
    """
    with app.app_context():
        from models import Investment, Transaction, SystemSetting
        
        logger.info("--- Starting Profit Backfill & Recovery ---")
        
        ref_setting = db.session.get(SystemSetting, 'referral_percentage')
        ref_percent = Decimal(ref_setting.value) if ref_setting else Decimal('2.0')
        
        active_investments = Investment.query.filter_by(status='active').all()
        today = datetime.utcnow().date()
        total_recovered = 0
        
        for inv in active_investments:
            try:
                # تعیین تاریخ شروع بررسی: یک روز بعد از آخرین سود، یا تاریخ شروع سرمایه‌گذاری
                if inv.last_profit_date:
                    current_date = inv.last_profit_date + timedelta(days=1)
                else:
                    current_date = inv.start_date.date()
                
                # حلقه برای تک تک روزهای عقب افتاده تا امروز
                while current_date <= today:
                    # 1. چک کردن اینکه آیا برای این روز خاص قبلاً سود واریز شده؟ (بسیار مهم)
                    existing_tx = Transaction.query.filter(
                        Transaction.investment_id == inv.id,
                        Transaction.type == 'profit',
                        func.date(Transaction.timestamp) == current_date
                    ).first()
                    
                    if existing_tx:
                        # اگر قبلاً واریز شده، برو به روز بعد
                        current_date += timedelta(days=1)
                        continue
                    
                    # 2. محاسبه سود
                    daily_profit = (inv.amount * (inv.plan.annual_return_rate / Decimal('100.0'))) / Decimal('365.0')
                    daily_profit = daily_profit.quantize(Decimal('0.0001'))
                    
                    # تنظیم ساعت واریز به ۱۲ ظهر همان روز تاریخی
                    payout_timestamp = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=12)
                    
                    # 3. ثبت تراکنش
                    user_tx = Transaction(
                        user_id=inv.user_id,
                        investment_id=inv.id,
                        type='profit',
                        amount=daily_profit,
                        description=f"Recovered profit for {current_date}",
                        status='completed',
                        timestamp=payout_timestamp
                    )
                    db.session.add(user_tx)
                    
                    # 4. پاداش معرف
                    if inv.user.referrer_id:
                        bonus = (daily_profit * (ref_percent / Decimal('100.0'))).quantize(Decimal('0.0001'))
                        if bonus > Decimal('0'):
                            ref_tx = Transaction(
                                user_id=inv.user.referrer_id,
                                type='referral_bonus',
                                amount=bonus,
                                description=f"Referral bonus recovery {current_date}",
                                status='completed',
                                timestamp=payout_timestamp
                            )
                            db.session.add(ref_tx)
                    
                    # آپدیت آخرین تاریخ سود
                    if not inv.last_profit_date or current_date > inv.last_profit_date:
                        inv.last_profit_date = current_date
                        
                    db.session.commit()
                    logger.info(f"Recovered profit for Investment {inv.id} on {current_date}")
                    total_recovered += 1
                    
                    current_date += timedelta(days=1)
                    
            except Exception as e:
                logger.error(f"Error recovering investment {inv.id}: {e}")
                db.session.rollback()
                
        logger.info(f"--- Backfill Completed. Total recovered payouts: {total_recovered} ---")
        return total_recovered