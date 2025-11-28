from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# راه‌اندازی SQLAlchemy
db = SQLAlchemy()

# ==========================================
# 1. تنظیمات سیستم (System Settings)
# ==========================================
class SystemSetting(db.Model):
    """
    جدول ذخیره تنظیمات کلی سیستم.
    مثل: درصد سود رفرال، آدرس کیف پول‌های شرکت و متن حساب بانکی.
    """
    key = db.Column(db.String(50), primary_key=True) # کلید تنظیم (مثلاً referral_percentage)
    value = db.Column(db.String(200))                # مقدار تنظیم

# ==========================================
# 2. نقش‌ها و دسترسی‌ها (RBAC)
# ==========================================
class Role(db.Model):
    """
    جدول نقش‌های کاربری.
    هر نقش مجموعه‌ای از دسترسی‌ها (Permissions) را دارد.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False) # نام نقش (مثلاً Admin, Support)
    description = db.Column(db.String(200))                      # توضیحات نقش
    
    # دسترسی‌ها به صورت متن جدا شده با ویرگول ذخیره می‌شوند
    # مثال: "manage_users,manage_kyc,view_ledger"
    permissions = db.Column(db.Text) 

    # ارتباط با کاربران (یک نقش می‌تواند متعلق به چندین کاربر باشد)
    users = db.relationship('User', backref='role', lazy=True)

# ==========================================
# 3. کاربران (Users)
# ==========================================
class User(UserMixin, db.Model):
    """جدول اصلی اطلاعات کاربران"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    first_name = db.Column(db.String(150), nullable=False)
    last_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50))
    
    # نقش کاربر (ارتباط با جدول Role)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    
    # وضعیت احراز هویت (not_submitted, pending, verified, rejected)
    kyc_status = db.Column(db.String(20), default='not_submitted')
    
    # پروفایل ریسک (not_assessed, conservative, balanced, aggressive)
    risk_profile = db.Column(db.String(20), default='not_assessed')
    risk_score = db.Column(db.Integer, default=0) 
    
    # اطلاعات کیف پول (برای واریز سود)
    wallet_network = db.Column(db.String(50))  
    wallet_address = db.Column(db.String(200)) 
    
    # سیستم رفرال (معرف)
    referral_code = db.Column(db.String(20), unique=True) 
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id')) 
    
    # تنظیمات امنیتی (تایید ایمیل و 2FA)
    is_email_verified = db.Column(db.Boolean, default=False)
    email_verification_code = db.Column(db.String(6))
    is_2fa_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(32)) # کلید امنیتی گوگل آتنتیکیتور
    
    # رابطه بازگشتی برای دیدن زیرمجموعه‌ها
    referrals = db.relationship('User', backref=db.backref('referrer', remote_side=[id]), lazy=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # روابط با سایر جداول
    investments = db.relationship('Investment', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    tickets = db.relationship('Ticket', backref='user', lazy=True)
    kyc_requests = db.relationship('KYCRequest', backref='user', lazy=True)


# ==========================================
# 4. پلن‌های سرمایه‌گذاری
# ==========================================
class InvestmentPlan(db.Model):
    """پکیج‌های سرمایه‌گذاری قابل خرید"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    duration_months = db.Column(db.Integer, nullable=False)
    annual_return_rate = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(500))
    
    # سطح ریسک (low, medium, high) برای فیلتر هوشمند
    risk_level = db.Column(db.String(20), default='low') 
    is_active = db.Column(db.Boolean, default=True)


# ==========================================
# 5. سرمایه‌گذاری‌های فعال
# ==========================================
class Investment(db.Model):
    """سرمایه‌گذاری‌های انجام شده توسط کاربران"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('investment_plan.id'), nullable=False)
    
    plan = db.relationship('InvestmentPlan', backref='investments')
    amount = db.Column(db.Float, nullable=False)
    
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    
    # وضعیت: pending_payment, active, completed
    status = db.Column(db.String(20), default='pending_payment')
    
    payment_proof_url = db.Column(db.String(500)) 
    payment_tx_id = db.Column(db.String(100))
    
    # تاریخ آخرین پرداخت سود (جهت جلوگیری از پرداخت تکراری)
    last_profit_date = db.Column(db.Date)


# ==========================================
# 6. تراکنش‌ها (دفتر کل)
# ==========================================
class Transaction(db.Model):
    """ثبت تمامی وقایع مالی سیستم"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # نوع: deposit, withdrawal, profit, referral_bonus
    type = db.Column(db.String(20), nullable=False)
    
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    tx_hash = db.Column(db.String(100))


# ==========================================
# 7. تیکت‌های پشتیبانی
# ==========================================
class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    status = db.Column(db.String(20), default='open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('TicketMessage', backref='ticket', lazy=True)

class TicketMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    sender_type = db.Column(db.String(10), nullable=False) # user یا admin
    message = db.Column(db.Text, nullable=False)
    attachment_url = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# ==========================================
# 8. درخواست‌های KYC
# ==========================================
class KYCRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    id_document_url = db.Column(db.String(500), nullable=False)
    address_document_url = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), default='pending')
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    admin_notes = db.Column(db.String(500))

# ==========================================
# 8. لاگهای ادمین (Audit Logs)
# ==========================================
class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # e.g., "Changed Role"
    details = db.Column(db.String(500))                 # e.g., "Changed User #5 role to Support"
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to see who performed the action
    user = db.relationship('User', backref='logs', lazy=True)