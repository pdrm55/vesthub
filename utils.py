import os
import re
import random
import string
import threading
from decimal import Decimal
from datetime import datetime
from flask import current_app, request, render_template_string
from flask_login import current_user
from flask_mail import Message
from werkzeug.utils import secure_filename
from extensions import db, mail
from models import User, Transaction, SystemSetting, AuditLog

# --- Security & Permissions ---

def has_permission(perm_name):
    if not current_user.is_authenticated or not current_user.role:
        return False
    if current_user.role.name == 'Admin':
        return True
    role_perms = current_user.role.permissions.split(',') if current_user.role.permissions else []
    return perm_name in role_perms

def log_admin_activity(action, details):
    if current_user.is_authenticated and current_user.role:
        if current_user.role.name == 'Admin' or current_user.role.permissions:
            try:
                log = AuditLog(
                    user_id=current_user.id,
                    action=action,
                    details=details,
                    ip_address=request.remote_addr
                )
                db.session.add(log)
                db.session.commit()
            except Exception as e:
                print(f"Error logging activity: {e}")
                db.session.rollback()

def is_strong_password(password):
    if len(password) < 8: return False
    if not re.search(r"[A-Z]", password): return False
    if not re.search(r"\d", password): return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password): return False
    return True

def generate_referral_code():
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not User.query.filter_by(referral_code=code).first():
            return code

# --- Financial Utilities ---

def get_setting(key, default=''):
    setting = db.session.get(SystemSetting, key)
    return setting.value if setting else default

def set_setting(key, value):
    setting = db.session.get(SystemSetting, key)
    if not setting:
        setting = SystemSetting(key=key)
        db.session.add(setting)
    setting.value = value
    db.session.commit()

def get_withdrawable_balance(user_id):
    earnings = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id, 
        Transaction.type.in_(['profit', 'referral_bonus']), 
        Transaction.status == 'completed'
    ).scalar() or Decimal('0.0')
    
    withdrawals = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id, 
        Transaction.type == 'withdrawal', 
        Transaction.status.in_(['pending', 'completed'])
    ).scalar() or Decimal('0.0')
    
    return earnings - withdrawals

# --- File Utilities ---

def validate_file_header(file_stream):
    header = file_stream.read(10)
    file_stream.seek(0)
    if header.startswith(b'\xFF\xD8\xFF'): return 'jpg'
    if header.startswith(b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'): return 'png'
    if header.startswith(b'%PDF-'): return 'pdf'
    return None

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file_obj):
    if not file_obj or file_obj.filename == '':
        return None

    if allowed_file(file_obj.filename):
        real_type = validate_file_header(file_obj.stream)
        ext = file_obj.filename.rsplit('.', 1)[1].lower()
        valid_types = {'jpg': ['jpg', 'jpeg'], 'png': ['png'], 'pdf': ['pdf']}
        
        if real_type and ext not in valid_types.get(real_type, []):
             print(f"Security Alert: File header ({real_type}) mismatch with extension ({ext})")
             return None
        
        filename = secure_filename(file_obj.filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S_")
        final_name = timestamp + filename
        
        upload_path = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_path, exist_ok=True)
        
        file_obj.save(os.path.join(upload_path, final_name))
        return final_name
    return None

# --- Real Email System (Async) ---

def send_async_email(app, msg):
    """ارسال ایمیل در پس‌زمینه"""
    with app.app_context():
        try:
            mail.send(msg)
            print(f"✅ Email sent to {msg.recipients}")
        except Exception as e:
            print(f"❌ Failed to send email: {e}")

def send_system_email(subject, recipient, body):
    """
    آماده‌سازی ایمیل و ارسال آن در ترد جداگانه
    """
    try:
        # استفاده از پروکسی شیء اپلیکیشن برای ترد
        app = current_app._get_current_object()
        
        msg = Message(subject, recipients=[recipient])
        msg.body = body
        # نسخه HTML ساده برای نمایش بهتر
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
            <h2 style="color: #0d6efd;">VestHub Notification</h2>
            <p style="font-size: 16px;">{body}</p>
            <hr>
            <small style="color: #666;">This is an automated message, please do not reply.</small>
        </div>
        """
        
        # اجرای ارسال در ترد جدید تا کاربر منتظر نماند
        thr = threading.Thread(target=send_async_email, args=(app, msg))
        thr.start()
        
    except Exception as e:
        print(f"Error initiating email: {e}")