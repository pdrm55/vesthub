from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask_mail import Mail, Message 
import os
import random
import string
import atexit
import re 
import pyotp 

# --- ایمپورت مدل‌ها ---
from models import db, User, Role, InvestmentPlan, Investment, Transaction, Ticket, KYCRequest, SystemSetting, TicketMessage, AuditLog

# ==========================================
# تنظیمات برنامه (App Configuration)
# ==========================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev_secret_key_change_this_in_production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vesthub.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# تنظیمات ایمیل (برای تست)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_app_password'
app.config['MAIL_DEFAULT_SENDER'] = ('VestHub Security', 'noreply@vesthub.com')

mail = Mail(app)

# تنظیمات آپلود
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'} 
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==========================================
# تنظیمات RBAC (لیست دسترسی‌ها)
# ==========================================
PERMISSIONS = {
    'manage_users': 'مدیریت کاربران (مشاهده، تغییر نقش)',
    'manage_plans': 'مدیریت پکیج‌های سرمایه‌گذاری',
    'view_ledger': 'مشاهده حسابداری و دفتر کل',
    'manage_payments': 'تایید یا رد واریزی‌ها',
    'manage_withdrawals': 'تایید یا رد برداشت‌ها',
    'manage_tickets': 'پاسخگویی به تیکت‌های پشتیبانی',
    'manage_kyc': 'بررسی و تایید مدارک هویتی',
    'manage_settings': 'دسترسی به تنظیمات سیستم و کیف پول‌ها',
    'manage_roles': 'مدیریت نقش‌ها (مخصوص سوپر ادمین)',
    'view_logs': 'مشاهده لاگ‌های سیستم'
}

def has_permission(perm_name):
    """
    بررسی می‌کند که آیا کاربر جاری دسترسی لازم را دارد یا خیر.
    نقش 'Admin' به همه چیز دسترسی دارد.
    """
    if not current_user.is_authenticated or not current_user.role:
        return False
    
    # سوپر ادمین همیشه دسترسی دارد
    if current_user.role.name == 'Admin':
        return True
        
    # بررسی لیست دسترسی‌های نقش کاربر
    role_perms = current_user.role.permissions.split(',') if current_user.role.permissions else []
    return perm_name in role_perms

# اضافه کردن تابع به محیط قالب‌ها
app.jinja_env.globals.update(has_permission=has_permission)

# ==========================================
# توابع کمکی
# ==========================================

# راه‌اندازی اکستنشن‌ها
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def log_admin_activity(action, details):
    """ثبت لاگ فعالیت‌های مدیریتی"""
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
            except:
                db.session.rollback()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file_obj):
    """ذخیره امن فایل آپلود شده"""
    if file_obj and allowed_file(file_obj.filename):
        filename = secure_filename(file_obj.filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S_")
        final_name = timestamp + filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], final_name)
        file_obj.save(file_path)
        return final_name
    return None

def generate_referral_code():
    """تولید کد رفرال یکتا"""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not User.query.filter_by(referral_code=code).first():
            return code

def is_strong_password(password):
    """بررسی قدرت رمز عبور"""
    if len(password) < 8: return False
    if not re.search(r"[A-Z]", password): return False
    if not re.search(r"\d", password): return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password): return False
    return True

def send_system_email(subject, recipient, body):
    print(f"\n[📧 EMAIL SIMULATION] To: {recipient} | Subject: {subject}")
    print(f"Body: {body}\n")

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
    ).scalar() or 0.0
    
    withdrawals = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id, 
        Transaction.type == 'withdrawal', 
        Transaction.status.in_(['pending', 'completed'])
    ).scalar() or 0.0
    
    return earnings - withdrawals

# ==========================================
# موتور توزیع سود
# ==========================================
def run_profit_distribution():
    with app.app_context():
        print(f"--- Starting Profit Distribution: {datetime.now()} ---")
        ref_percent = float(get_setting('referral_percentage', '2.0'))
        active_investments = Investment.query.filter_by(status='active').all()
        today = datetime.utcnow().date()
        count = 0
        
        for inv in active_investments:
            if inv.last_profit_date == today: 
                continue

            annual_rate = inv.plan.annual_return_rate
            daily_profit = round((inv.amount * (annual_rate / 100.0)) / 365.0, 4)
            
            user_tx = Transaction(
                user_id=inv.user_id,
                type='profit',
                amount=daily_profit,
                description=f"Daily Profit",
                status='completed',
                timestamp=datetime.utcnow()
            )
            db.session.add(user_tx)
            
            if inv.user.referrer_id:
                bonus = round(daily_profit * (ref_percent / 100.0), 4)
                if bonus > 0:
                    ref_tx = Transaction(
                        user_id=inv.user.referrer_id,
                        type='referral_bonus',
                        amount=bonus,
                        description=f"Ref Bonus",
                        status='completed',
                        timestamp=datetime.utcnow()
                    )
                    db.session.add(ref_tx)
            
            inv.last_profit_date = today
            count += 1
        
        db.session.commit()
        return count

# ==========================================
# راه‌اندازی اولیه (Init Data)
# ==========================================
with app.app_context():
    db.create_all()
    
    # 1. نقش‌ها
    if not Role.query.first():
        db.session.add(Role(name='Admin', description='Super Admin', permissions='all'))
        db.session.add(Role(name='Investor', description='Standard User', permissions=''))
        db.session.add(Role(name='Support', description='Support Agent', permissions='manage_tickets'))
        db.session.commit()
        
    # 2. تنظیمات
    if not db.session.get(SystemSetting, 'referral_percentage'):
        db.session.add(SystemSetting(key='referral_percentage', value='2.0'))
        db.session.commit()
        
    # 3. ادمین
    if not User.query.filter_by(email='admin@vesthub.com').first():
        role_admin = Role.query.filter_by(name='Admin').first()
        admin = User(
            email='admin@vesthub.com', 
            password=generate_password_hash('admin123', method='pbkdf2:sha256'), 
            first_name='Admin', last_name='User', 
            role=role_admin, referral_code='ADMIN001', is_email_verified=True
        )
        db.session.add(admin)
        db.session.commit()
        
    # 4. پلن‌ها
    if not InvestmentPlan.query.first():
        plans = [
            InvestmentPlan(name="Safe Starter 3M", duration_months=3, annual_return_rate=4.0, risk_level='low'),
            InvestmentPlan(name="High Yield 12M", duration_months=12, annual_return_rate=18.0, risk_level='high')
        ]
        db.session.bulk_save_objects(plans)
        db.session.commit()

# ==========================================
# روت‌های عمومی (Public Routes)
# ==========================================
@app.route('/')
def home():
    if request.args.get('ref'): 
        session['ref_code'] = request.args.get('ref')
    plans = InvestmentPlan.query.filter_by(is_active=True).order_by(InvestmentPlan.duration_months.desc()).all()
    return render_template('index.html', plans=plans)

@app.route('/invest')
def invest():
    return render_template('learn.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/plans')
def plans():
    plans = InvestmentPlan.query.filter_by(is_active=True).order_by(InvestmentPlan.duration_months.desc()).all()
    return render_template('plans.html', plans=plans)

@app.route('/marketplace')
def marketplace():
    return render_template('marketplace.html')

# ==========================================
# روت‌های احراز هویت (Auth)
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: 
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            # چک ایمیل
            if not user.is_email_verified:
                session['unverified_user_id'] = user.id
                return redirect(url_for('verify_email'))
            # چک 2FA
            if user.is_2fa_enabled:
                session['2fa_user_id'] = user.id
                return redirect(url_for('verify_2fa_login'))
            
            login_user(user)
            log_admin_activity('Login', 'User logged in')
            
            # ریدایرکت هوشمند
            if user.role.name == 'Admin' or user.role.permissions:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.', 'danger')
    return render_template('login.html')

# روت لاگین ادمین (که در نسخه شما نبود)
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
        
    if request.method == 'POST':
        # برای سادگی، همان لاگین معمولی است ولی با چک کردن نقش
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
             if user.role.name == 'Admin' or user.role.permissions:
                 login_user(user)
                 return redirect(url_for('admin_dashboard'))
             else:
                 flash('Access Denied. You are not an admin.', 'danger')
        else:
            flash('Invalid credentials.', 'danger')
            
    return render_template('admin_login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated: 
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if User.query.filter_by(email=email).first():
            flash('Email exists.', 'warning')
            return redirect(url_for('signup'))
            
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('signup'))

        if not is_strong_password(password):
            flash('Password too weak.', 'danger')
            return redirect(url_for('signup'))

        role_investor = Role.query.filter_by(name='Investor').first()
        ver_code = ''.join(random.choices(string.digits, k=6))
        ref_code = request.form.get('referral_code') or session.get('ref_code')
        referrer_id = None
        if ref_code:
            ref_user = User.query.filter_by(referral_code=ref_code).first()
            if ref_user: referrer_id = ref_user.id

        new_user = User(
            email=email, 
            password=generate_password_hash(password, method='pbkdf2:sha256'),
            first_name=request.form.get('first_name'), 
            last_name=request.form.get('last_name'),
            phone=request.form.get('phone'), 
            role=role_investor, 
            referral_code=generate_referral_code(), 
            referrer_id=referrer_id,
            is_email_verified=False, 
            email_verification_code=ver_code
        )
        db.session.add(new_user)
        db.session.commit()
        
        send_system_email("Verify Account", email, f"Code: {ver_code}")
        session['unverified_user_id'] = new_user.id
        return redirect(url_for('verify_email'))
        
    return render_template('signup.html')

@app.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    if 'unverified_user_id' not in session: 
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user = db.session.get(User, session['unverified_user_id'])
        if user and user.email_verification_code == request.form.get('code'):
            user.is_email_verified = True
            db.session.commit()
            login_user(user)
            session.pop('unverified_user_id', None)
            return redirect(url_for('dashboard'))
        flash('Invalid code', 'danger')
    return render_template('verify_email.html')

@app.route('/verify-2fa-login', methods=['GET', 'POST'])
def verify_2fa_login():
    if '2fa_user_id' not in session: 
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user = db.session.get(User, session['2fa_user_id'])
        if pyotp.TOTP(user.two_factor_secret).verify(request.form.get('code')):
            login_user(user)
            session.pop('2fa_user_id', None)
            if user.role.name == 'Admin': 
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
        flash('Invalid code', 'danger')
    return render_template('two_factor_verify.html')

@app.route('/logout')
@login_required
def logout(): 
    logout_user()
    return redirect(url_for('login'))

@app.route('/forgot-password')
def forgot_password(): 
    return render_template('forgot-password.html')

# ==========================================
# داشبورد کاربر (User Dashboard)
# ==========================================
@app.route('/dashboard')
@login_required
def dashboard():
    total_invested = sum(inv.amount for inv in current_user.investments if inv.status in ['active', 'pending_payment'])
    total_profit = get_withdrawable_balance(current_user.id)
    referral_count = User.query.filter_by(referrer_id=current_user.id).count()
    referral_earnings = db.session.query(db.func.sum(Transaction.amount)).filter_by(user_id=current_user.id, type='referral_bonus', status='completed').scalar() or 0.0
    return render_template('dashboard.html', user=current_user, total_invested=total_invested, total_profit=total_profit, referral_count=referral_count, referral_earnings=referral_earnings, active_investments=current_user.investments)

@app.route('/invest-plans')
@login_required
def invest_plans():
    if current_user.risk_profile == 'not_assessed': 
        return redirect(url_for('risk_assessment'))
    
    base = InvestmentPlan.query.filter_by(is_active=True).order_by(InvestmentPlan.duration_months.desc())
    
    if current_user.risk_profile == 'conservative': 
        plans = base.filter(InvestmentPlan.risk_level == 'low').all()
    elif current_user.risk_profile == 'balanced': 
        plans = base.filter(InvestmentPlan.risk_level.in_(['low', 'medium'])).all()
    else: 
        plans = base.all()
    return render_template('invest-plans.html', plans=plans)

@app.route('/create-investment', methods=['POST'])
@login_required
def create_investment():
    new_inv = Investment(user_id=current_user.id, plan_id=request.form.get('plan_id'), amount=float(request.form.get('amount')), status='pending_payment', start_date=datetime.utcnow())
    db.session.add(new_inv)
    db.session.commit()
    return redirect(url_for('investment_pending', investment_id=new_inv.id))

@app.route('/invest/pending/<int:investment_id>')
@login_required
def investment_pending(investment_id):
    inv = Investment.query.get_or_404(investment_id)
    wallets = {'trc20': get_setting('wallet_trc20'), 'erc20': get_setting('wallet_erc20'), 'bep20': get_setting('wallet_bep20'), 'polygon': get_setting('wallet_polygon'), 'bank': get_setting('bank_details')}
    return render_template('investment_pending.html', investment=inv, wallets=wallets)

@app.route('/invest/submit-proof/<int:investment_id>', methods=['POST'])
@login_required
def submit_proof(investment_id):
    inv = Investment.query.get_or_404(investment_id)
    tx_hash = request.form.get('txnHash')
    inv.payment_tx_id = tx_hash
    db.session.add(Transaction(user_id=current_user.id, type='deposit', amount=inv.amount, status='pending', tx_hash=tx_hash))
    db.session.commit()
    flash('Proof submitted', 'success')
    return redirect(url_for('dashboard'))

@app.route('/payment/process/<int:investment_id>', methods=['POST'])
@login_required
def process_online_payment(investment_id):
    inv = Investment.query.get_or_404(investment_id)
    inv.status = 'active'
    inv.start_date = datetime.utcnow()
    inv.payment_tx_id = f"ONLINE-{random.randint(1000,9999)}"
    db.session.add(Transaction(user_id=current_user.id, type='deposit', amount=inv.amount, status='completed', tx_hash=inv.payment_tx_id))
    db.session.commit()
    flash('Paid online successfully', 'success')
    return redirect(url_for('dashboard'))

@app.route('/withdrawal', methods=['GET', 'POST'])
@login_required
def withdrawal():
    if current_user.kyc_status != 'verified': 
        return redirect(url_for('settings'))
    
    if request.method == 'POST':
        amt = float(request.form.get('amount'))
        if amt <= get_withdrawable_balance(current_user.id):
            db.session.add(Transaction(user_id=current_user.id, type='withdrawal', amount=amt, status='pending'))
            db.session.commit()
            flash('Requested', 'success')
    return render_template('withdrawal.html', available_balance=get_withdrawable_balance(current_user.id), locked_balance=0, history=Transaction.query.filter_by(user_id=current_user.id, type='withdrawal').all())

@app.route('/wallet', methods=['GET', 'POST'])
@login_required
def wallet():
    if request.method == 'POST': 
        current_user.wallet_network=request.form.get('wallet_type')
        current_user.wallet_address=request.form.get('wallet_address')
        db.session.commit()
    return render_template('wallet.html', user=current_user)

@app.route('/settings', methods=['GET'])
@login_required
def settings():
    return render_template('settings.html', user=current_user, kyc_request=KYCRequest.query.filter_by(user_id=current_user.id).first())

@app.route('/settings/enable-2fa', methods=['POST'])
@login_required
def enable_2fa():
    secret = pyotp.random_base32()
    current_user.two_factor_secret = secret
    db.session.commit()
    return {'secret': secret, 'uri': pyotp.totp.TOTP(secret).provisioning_uri(name=current_user.email, issuer_name='VestHub')}

@app.route('/settings/confirm-2fa', methods=['POST'])
@login_required
def confirm_2fa():
    if pyotp.TOTP(current_user.two_factor_secret).verify(request.form.get('code')): 
        current_user.is_2fa_enabled = True
        db.session.commit()
        flash('2FA Enabled', 'success')
    else: 
        flash('Invalid code', 'danger')
    return redirect(url_for('settings'))

@app.route('/settings/submit-kyc', methods=['POST'])
@login_required
def submit_kyc():
    id_f = request.files.get('idDoc')
    ad_f = request.files.get('addressDoc')
    if id_f and ad_f:
        current_user.kyc_status = 'pending'
        db.session.add(KYCRequest(user_id=current_user.id, id_document_url=save_uploaded_file(id_f), address_document_url=save_uploaded_file(ad_f), status='pending'))
        db.session.commit()
        flash('KYC Submitted', 'success')
    return redirect(url_for('settings'))

@app.route('/risk-assessment', methods=['GET', 'POST'])
@login_required
def risk_assessment():
    if request.method == 'POST': 
        current_user.risk_profile='balanced'
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('risk_assessment.html')

# --- سایر روت‌های کاربر (Support, Charts, Trader) ---
@app.route('/support', methods=['GET', 'POST'])
@login_required
def support():
    if request.method == 'POST':
        tk = Ticket(user_id=current_user.id, subject=request.form.get('subject'), category=request.form.get('category'), status='open')
        db.session.add(tk)
        db.session.commit()
        db.session.add(TicketMessage(ticket_id=tk.id, sender_type='user', message=request.form.get('message')))
        db.session.commit()
        return redirect(url_for('support'))
    return render_template('support.html', tickets=Ticket.query.filter_by(user_id=current_user.id).all())

@app.route('/support/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def ticket_view(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if request.method == 'POST':
        db.session.add(TicketMessage(ticket_id=ticket.id, sender_type='user', message=request.form.get('message')))
        ticket.status='open'
        db.session.commit()
    return render_template('support_view.html', ticket=ticket)

@app.route('/api/chart/user-data')
@login_required
def api_user_data(): 
    return jsonify({'assets': {'invested':0, 'profit':0, 'referral':0}})

@app.route('/trader/dashboard')
@login_required
def trader_dashboard(): 
    return render_template('trader_dashboard.html', user=current_user)

@app.route('/trader/api')
@login_required
def trader_api(): 
    return render_template('trader_api.html')

@app.route('/trader/subscription')
@login_required
def trader_subscription(): 
    return render_template('trader_subscription.html')

# ==========================================
# روت‌های پنل ادمین با RBAC
# ==========================================

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # چک می‌کنیم کاربر ادمین است یا پرمیشن دارد
    if not current_user.role: 
        return redirect(url_for('home'))
    return render_template('admin_dashboard.html')

# --- مدیریت نقش‌ها (Roles) ---
@app.route('/admin/roles', methods=['GET', 'POST'])
@login_required
def admin_roles():
    if not has_permission('manage_roles'):
        flash('شما دسترسی به مدیریت نقش‌ها ندارید.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        desc = request.form.get('description')
        # دریافت لیست پرمیشن‌های تیک‌خورده از فرم
        perms_list = request.form.getlist('permissions')
        perms_str = ",".join(perms_list) # ذخیره به صورت متن CSV
        
        db.session.add(Role(name=name, description=desc, permissions=perms_str))
        db.session.commit()
        log_admin_activity('Create Role', f'Created role: {name}')
        flash('نقش جدید با موفقیت ایجاد شد.', 'success')
        return redirect(url_for('admin_roles'))
        
    return render_template('admin_roles.html', roles=Role.query.all(), all_permissions=PERMISSIONS)

@app.route('/admin/roles/edit/<int:role_id>', methods=['POST'])
@login_required
def admin_edit_role(role_id):
    if not has_permission('manage_roles'): 
        return redirect(url_for('admin_dashboard'))
    
    role = Role.query.get_or_404(role_id)
    if role.name == 'Admin':
        flash('نقش سوپر ادمین قابل ویرایش نیست.', 'warning')
        return redirect(url_for('admin_roles'))
        
    role.name = request.form.get('name')
    role.description = request.form.get('description')
    # بروزرسانی پرمیشن‌ها
    role.permissions = ",".join(request.form.getlist('permissions'))
    
    db.session.commit()
    log_admin_activity('Edit Role', f'Edited role: {role.name}')
    flash('نقش ویرایش شد.', 'success')
    return redirect(url_for('admin_roles'))

@app.route('/admin/roles/delete/<int:role_id>', methods=['POST'])
@login_required
def admin_delete_role(role_id):
    if not has_permission('manage_roles'): 
        return redirect(url_for('admin_dashboard'))
    
    role = Role.query.get_or_404(role_id)
    if role.name == 'Admin':
        flash('نقش سوپر ادمین قابل حذف نیست.', 'danger')
    elif role.users:
        flash('این نقش به کاربرانی اختصاص داده شده است.', 'warning')
    else:
        db.session.delete(role)
        db.session.commit()
        log_admin_activity('Delete Role', f'Deleted role: {role.name}')
        flash('نقش حذف شد.', 'success')
    return redirect(url_for('admin_roles'))

# --- مدیریت کاربران و تغییر نقش ---
@app.route('/admin/users')
@login_required
def admin_users():
    if not has_permission('manage_users'): 
        return redirect(url_for('admin_dashboard'))
    # ارسال لیست نقش‌ها برای مودال تغییر نقش
    return render_template('admin_users.html', users=User.query.all(), roles=Role.query.all())

@app.route('/admin/users/change-role/<int:user_id>', methods=['POST'])
@login_required
def admin_change_role(user_id):
    if not has_permission('manage_users'): 
        return redirect(url_for('admin_dashboard'))
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('شما نمی‌توانید نقش خودتان را تغییر دهید.', 'warning')
    else:
        user.role_id = request.form.get('new_role_id')
        db.session.commit()
        log_admin_activity('Change Role', f'Changed role for {user.email}')
        flash('نقش کاربر بروزرسانی شد.', 'success')
    return redirect(url_for('admin_users'))

# --- سایر بخش‌های ادمین (محافظت شده با has_permission) ---

@app.route('/admin/payments')
@login_required
def admin_payments():
    if has_permission('manage_payments'):
        return render_template('admin_payments.html', payments=Transaction.query.filter_by(type='deposit').all()) 
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/payments/approve/<int:tx_id>', methods=['POST'])
@login_required
def approve_payment(tx_id):
    if not has_permission('manage_payments'): 
        return redirect(url_for('admin_dashboard'))
    tx = db.session.get(Transaction, tx_id)
    tx.status='completed'
    db.session.commit()
    log_admin_activity('Approve Payment', f'Approved payment {tx.id}')
    return redirect(url_for('admin_payments'))

@app.route('/admin/payments/reject/<int:tx_id>', methods=['POST'])
@login_required
def reject_payment(tx_id):
    if not has_permission('manage_payments'): 
        return redirect(url_for('admin_dashboard'))
    tx = db.session.get(Transaction, tx_id)
    tx.status='rejected'
    db.session.commit()
    log_admin_activity('Reject Payment', f'Rejected payment {tx.id}')
    return redirect(url_for('admin_payments'))

@app.route('/admin/withdrawals')
@login_required
def admin_withdrawals():
    if has_permission('manage_withdrawals'):
        return render_template('admin_withdrawals.html', requests=Transaction.query.filter_by(type='withdrawal').all())
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/withdrawals/approve/<int:tx_id>', methods=['POST'])
@login_required
def approve_withdrawal(tx_id):
    if not has_permission('manage_withdrawals'): 
        return redirect(url_for('admin_dashboard'))
    tx = db.session.get(Transaction, tx_id)
    tx.status='completed'
    db.session.commit()
    log_admin_activity('Approve Withdrawal', f'Approved withdrawal {tx.id}')
    return redirect(url_for('admin_withdrawals'))

@app.route('/admin/withdrawals/reject/<int:tx_id>', methods=['POST'])
@login_required
def reject_withdrawal(tx_id):
    if not has_permission('manage_withdrawals'): 
        return redirect(url_for('admin_dashboard'))
    tx = db.session.get(Transaction, tx_id)
    tx.status='rejected'
    db.session.commit()
    log_admin_activity('Reject Withdrawal', f'Rejected withdrawal {tx.id}')
    return redirect(url_for('admin_withdrawals'))

@app.route('/admin/kyc')
@login_required
def admin_kyc():
    if has_permission('manage_kyc'):
        return render_template('admin_kyc.html', pending=KYCRequest.query.filter_by(status='pending').all(), history=[]) 
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/kyc/approve/<int:req_id>', methods=['POST'])
@login_required
def approve_kyc(req_id):
    if not has_permission('manage_kyc'): 
        return redirect(url_for('admin_dashboard'))
    req=db.session.get(KYCRequest, req_id)
    req.status='approved'
    req.user.kyc_status='verified'
    db.session.commit()
    log_admin_activity('Approve KYC', f'Approved KYC for {req.user.email}')
    return redirect(url_for('admin_kyc'))

@app.route('/admin/kyc/reject/<int:req_id>', methods=['POST'])
@login_required
def reject_kyc(req_id):
    if not has_permission('manage_kyc'): 
        return redirect(url_for('admin_dashboard'))
    req=db.session.get(KYCRequest, req_id)
    req.status='rejected'
    req.user.kyc_status='rejected'
    db.session.commit()
    log_admin_activity('Reject KYC', f'Rejected KYC for {req.user.email}')
    return redirect(url_for('admin_kyc'))

@app.route('/admin/support')
@login_required
def admin_support():
    if has_permission('manage_tickets'):
        return render_template('admin_support.html', open_tickets=Ticket.query.all(), closed_tickets=[]) 
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/support/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def admin_ticket_view(ticket_id):
    if not has_permission('manage_tickets'): 
        return redirect(url_for('admin_dashboard'))
    ticket = db.session.get(Ticket, ticket_id)
    # ... reply logic ...
    return render_template('admin_support_view.html', ticket=ticket)

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    if not has_permission('manage_settings'): 
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST': 
        for k in ['wallet_trc20', 'bank_details', 'referral_percentage']: set_setting(k, request.form.get(k))
        log_admin_activity('Update Settings', 'Changed system settings')
    return render_template('admin_settings.html', config={})

@app.route('/admin/accounting')
@login_required
def admin_accounting():
    if not has_permission('view_ledger'): 
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_accounting.html', transactions=Transaction.query.all())

@app.route('/admin/plans', methods=['GET', 'POST'])
@login_required
def admin_plans():
    if not has_permission('manage_plans'): 
        return redirect(url_for('admin_dashboard'))
    if request.method=='POST': 
        db.session.add(InvestmentPlan(name=request.form.get('name'), duration_months=12, annual_return_rate=10))
        db.session.commit()
        log_admin_activity('Create Plan', 'Created new investment plan')
    return render_template('admin_plans.html', plans=InvestmentPlan.query.all())

@app.route('/admin/logs')
@login_required
def admin_logs():
    if not has_permission('view_logs'): 
        return redirect(url_for('admin_dashboard'))
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('admin_logs.html', logs=logs)

@app.route('/api/chart/admin-stats')
@login_required
def api_admin_stats(): 
    return jsonify({'dates':[], 'counts':[]})

@app.route('/test/distribute-profit', methods=['POST'])
@login_required
def distribute_test_profit():
    if not has_permission('manage_settings'): 
        return redirect(url_for('home'))
    run_profit_distribution()
    log_admin_activity('Distribute Profit', 'Manually triggered profit distribution')
    return redirect(url_for('admin_accounting'))

if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=run_profit_distribution, trigger="cron", hour=0, minute=0)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
    app.run(debug=True, host='0.0.0.0', port=5000)