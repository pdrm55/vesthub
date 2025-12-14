import random
import string
import secrets
import pyotp
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from extensions import db, oauth
from models import User, Role
from utils import is_strong_password, generate_referral_code, send_system_email, log_admin_activity

auth_bp = Blueprint('auth', __name__)

# --- Helper for Password Reset Token ---
def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: 
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            if not user.is_email_verified:
                session['unverified_user_id'] = user.id
                return redirect(url_for('auth.verify_email'))
            
            login_user(user)
            log_admin_activity('Login', 'User logged in via standard form')
            
            if user.role.name == 'Admin' or user.role.permissions:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('user.dashboard'))
            
        flash('Invalid email or password.', 'danger')
        
    return render_template('login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated: 
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'warning')
            return redirect(url_for('auth.signup'))
            
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.signup'))

        if not is_strong_password(password):
            flash('Password is too weak. (Must include uppercase, number, and special character)', 'danger')
            return redirect(url_for('auth.signup'))

        role_investor = Role.query.filter_by(name='Investor').first()
        if not role_investor: role_investor = None

        ver_code = ''.join(random.choices(string.digits, k=6))
        
        ref_code = request.form.get('referral_code') or session.get('ref_code')
        referrer_id = None
        if ref_code:
            ref_user = User.query.filter_by(referral_code=ref_code).first()
            if ref_user: referrer_id = ref_user.id

        new_user = User(
            email=email, 
            password=generate_password_hash(password, method='pbkdf2:sha256'),
            first_name=first_name, 
            last_name=last_name,
            phone=request.form.get('phone'), 
            role=role_investor, 
            referral_code=generate_referral_code(), 
            referrer_id=referrer_id,
            is_email_verified=False, 
            email_verification_code=ver_code
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        send_system_email("Verify Account", email, f"Your Code: {ver_code}")
        session['unverified_user_id'] = new_user.id
        return redirect(url_for('auth.verify_email'))
        
    return render_template('signup.html')

@auth_bp.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    if 'unverified_user_id' not in session: 
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        user = db.session.get(User, session['unverified_user_id'])
        if user and user.email_verification_code == request.form.get('code'):
            user.is_email_verified = True
            db.session.commit()
            login_user(user)
            session.pop('unverified_user_id', None)
            flash('Your email has been verified. Welcome!', 'success')
            return redirect(url_for('user.dashboard'))
        flash('Invalid code.', 'danger')
    return render_template('verify_email.html')

@auth_bp.route('/verify-2fa-login', methods=['GET', 'POST'])
def verify_2fa_login():
    if '2fa_user_id' not in session: 
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        user = db.session.get(User, session['2fa_user_id'])
        if user.two_factor_secret and pyotp.TOTP(user.two_factor_secret).verify(request.form.get('code')):
            login_user(user)
            session.pop('2fa_user_id', None)
            if user.role.name == 'Admin': 
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('user.dashboard'))
        flash('Incorrect authentication code.', 'danger')
    return render_template('two_factor_verify.html')

@auth_bp.route('/logout')
@login_required
def logout(): 
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

# --- Social Login Routes ---

@auth_bp.route('/social-login/<provider>')
def social_login(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('user.dashboard'))
    
    client = oauth.create_client(provider)
    if not client:
        flash(f'{provider.title()} login is not configured.', 'warning')
        return redirect(url_for('auth.login'))
        
    redirect_uri = url_for('auth.social_auth_callback', provider=provider, _external=True)
    return client.authorize_redirect(redirect_uri)

@auth_bp.route('/social-login/<provider>/callback')
def social_auth_callback(provider):
    client = oauth.create_client(provider)
    if not client:
        return redirect(url_for('auth.login'))
        
    try:
        token = client.authorize_access_token()
        user_info = token.get('userinfo')
        if not user_info:
            user_info = client.userinfo()
            
        email = user_info.get('email')
        if not email:
            flash('Could not retrieve email from provider.', 'danger')
            return redirect(url_for('auth.login'))
            
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Create new user automatically
            first_name = user_info.get('given_name', 'User')
            last_name = user_info.get('family_name', '')
            
            role_investor = Role.query.filter_by(name='Investor').first()
            random_pw = secrets.token_urlsafe(16) # Secure random password
            
            # Handle referral if exists in session
            ref_code = session.get('ref_code')
            referrer_id = None
            if ref_code:
                ref_user = User.query.filter_by(referral_code=ref_code).first()
                if ref_user: referrer_id = ref_user.id

            user = User(
                email=email,
                password=generate_password_hash(random_pw, method='pbkdf2:sha256'),
                first_name=first_name,
                last_name=last_name,
                role=role_investor,
                referral_code=generate_referral_code(),
                referrer_id=referrer_id,
                is_email_verified=True # Trusted provider
            )
            db.session.add(user)
            db.session.commit()
            log_admin_activity('Signup', f'User signed up via {provider}')
            
        login_user(user)
        return redirect(url_for('user.dashboard'))
        
    except Exception as e:
        flash(f'Authentication failed: {str(e)}', 'danger')
        return redirect(url_for('auth.login'))

# --- Password Reset Logic (Added) ---

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        # ما حتی اگر ایمیل پیدا نشود، پیام موفقیت نشان می‌دهیم تا هکرها نتوانند ایمیل‌ها را چک کنند
        if user:
            s = get_serializer()
            # ایجاد توکن امن با ایمیل کاربر
            token = s.dumps(user.email, salt='password-reset-salt')
            
            # ساخت لینک بازیابی (آدرس کامل دامین)
            reset_link = url_for('auth.reset_password', token=token, _external=True)
            
            # ارسال ایمیل
            email_body = f"""
            <p>You requested a password reset for your VestHub account.</p>
            <p>Click the link below to reset your password (valid for 1 hour):</p>
            <a href="{reset_link}" style="background:#0d6efd;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;">Reset Password</a>
            <p>If you did not request this, please ignore this email.</p>
            """
            send_system_email("Password Reset Request", user.email, email_body)
        
        flash('If an account with that email exists, we have sent a password reset link.', 'info')
        return redirect(url_for('auth.login'))
        
    return render_template('forgot-password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    s = get_serializer()
    try:
        # توکن فقط برای ۱ ساعت (۳۶۰۰ ثانیه) معتبر است
        email = s.loads(token, salt='password-reset-salt', max_age=3600)
    except SignatureExpired:
        flash('The reset link has expired.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    except BadSignature:
        flash('Invalid reset link.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('reset_password.html', token=token)
            
        if not is_strong_password(password):
            flash('Password is too weak.', 'danger')
            return render_template('reset_password.html', token=token)
            
        user = User.query.filter_by(email=email).first()
        if user:
            user.password = generate_password_hash(password, method='pbkdf2:sha256')
            db.session.commit()
            flash('Your password has been updated! Please log in.', 'success')
            return redirect(url_for('auth.login'))
            
    return render_template('reset_password.html', token=token)