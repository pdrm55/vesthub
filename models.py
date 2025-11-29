"""
ماژول مدل‌های دیتابیس (SQLAlchemy Models).

این فایل شامل تعریف تمام جداول دیتابیس به صورت کلاس‌های پایتون است.
هر کلاس یک جدول و هر نمونه از آن کلاس یک ردیف در آن جدول را نمایندگی می‌کند.
"""

from datetime import datetime
from flask_login import UserMixin
from extensions import db

class SystemSetting(db.Model):
    """مدل برای ذخیره تنظیمات کلی سیستم به صورت زوج‌های کلید-مقدار."""
    __tablename__ = 'system_settings'
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(200))

# ==========================================
# 2. Roles & Permissions
# ==========================================
class Role(db.Model):
    """مدل برای تعریف نقش‌های کاربری (مانند ادمین، سرمایه‌گذار)."""
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    permissions = db.Column(db.Text)  # لیستی از دسترسی‌ها به صورت رشته جدا شده با کاما
    users = db.relationship('User', backref='role', lazy=True)

# ==========================================
# 3. Users
# ==========================================
class User(UserMixin, db.Model):
    """مدل اصلی کاربران سیستم."""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    first_name = db.Column(db.String(150), nullable=False)
    last_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50))
    # کلید خارجی برای ارتباط با جدول نقش‌ها
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    kyc_status = db.Column(db.String(20), default='not_submitted')  # وضعیت احراز هویت
    risk_profile = db.Column(db.String(20), default='not_assessed')
    risk_score = db.Column(db.Integer, default=0)
    wallet_network = db.Column(db.String(50))
    wallet_address = db.Column(db.String(200))
    referral_code = db.Column(db.String(20), unique=True)
    # کلید خارجی برای ارتباط با معرف (خود جدول کاربران)
    referrer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_email_verified = db.Column(db.Boolean, default=False)
    email_verification_code = db.Column(db.String(6))
    is_2fa_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(32))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # تعریف روابط (Relationships)
    referrals = db.relationship('User', backref=db.backref('referrer', remote_side=[id]), lazy=True)
    investments = db.relationship('Investment', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    tickets = db.relationship('Ticket', backref='user', lazy=True)
    kyc_requests = db.relationship('KYCRequest', backref='user', lazy=True)
    logs = db.relationship('AuditLog', backref='user', lazy=True)

# ==========================================
# 4. Investment Plans
# ==========================================
class InvestmentPlan(db.Model):
    """مدل برای تعریف پلن‌های سرمایه‌گذاری مختلف."""
    __tablename__ = 'investment_plans'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    duration_months = db.Column(db.Integer, nullable=False)
    
    # استفاده از Numeric برای ذخیره دقیق درصد سود سالانه (دقت کل ۱۰ رقم، ۲ رقم اعشار)
    annual_return_rate = db.Column(db.Numeric(10, 2), nullable=False)
    
    description = db.Column(db.String(500))
    risk_level = db.Column(db.String(20), default='low')
    is_active = db.Column(db.Boolean, default=True)

# ==========================================
# 5. Investments
# ==========================================
class Investment(db.Model):
    """مدل برای ثبت سرمایه‌گذاری‌های انجام شده توسط کاربران."""
    __tablename__ = 'investments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('investment_plans.id'), nullable=False)
    plan = db.relationship('InvestmentPlan', backref='investments')
    
    # استفاده از Numeric برای ذخیره دقیق مبلغ سرمایه‌گذاری (دقت کل ۱۵ رقم، ۴ رقم اعشار)
    amount = db.Column(db.Numeric(15, 4), nullable=False)
    
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending_payment')
    payment_proof_url = db.Column(db.String(500))
    payment_tx_id = db.Column(db.String(100))
    last_profit_date = db.Column(db.Date)

# ==========================================
# 6. Transactions (Ledger)
# ==========================================
class Transaction(db.Model):
    """مدل برای ثبت تمام تراکنش‌های مالی (دفتر کل)."""
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # نوع تراکنش: profit, withdrawal, deposit, ...
    
    # استفاده از Numeric برای ذخیره دقیق مبلغ تراکنش
    amount = db.Column(db.Numeric(15, 4), nullable=False)
    
    description = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    tx_hash = db.Column(db.String(100))

# ==========================================
# 7. Tickets & Messages
# ==========================================
class Ticket(db.Model):
    """مدل برای تیکت‌های پشتیبانی ارسال شده توسط کاربران."""
    __tablename__ = 'tickets'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    status = db.Column(db.String(20), default='open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('TicketMessage', backref='ticket', lazy=True)

class TicketMessage(db.Model):
    """مدل برای پیام‌های رد و بدل شده در یک تیکت پشتیبانی."""
    __tablename__ = 'ticket_messages'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    sender_type = db.Column(db.String(10), nullable=False)
    message = db.Column(db.Text, nullable=False)
    attachment_url = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ==========================================
# 8. KYC Requests
# ==========================================
class KYCRequest(db.Model):
    """مدل برای درخواست‌های احراز هویت (KYC) کاربران."""
    __tablename__ = 'kyc_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    id_document_url = db.Column(db.String(500), nullable=False)
    address_document_url = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), default='pending')
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    admin_notes = db.Column(db.String(500))

# ==========================================
# 9. Audit Logs
# ==========================================
class AuditLog(db.Model):
    """مدل برای ثبت لاگ فعالیت‌های مهم کاربران (مخصوصا ادمین‌ها)."""
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.String(500))
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)