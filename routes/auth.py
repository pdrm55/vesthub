import random
import string
import pyotp
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from models import User, Role
from utils import is_strong_password, generate_referral_code, send_system_email, log_admin_activity

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: 
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            # 1. Check email verification
            if not user.is_email_verified:
                session['unverified_user_id'] = user.id
                return redirect(url_for('auth.verify_email'))
            
            # 2. Check 2FA
            if user.is_2fa_enabled:
                session['2fa_user_id'] = user.id
                return redirect(url_for('auth.verify_2fa_login'))
            
            # Successful login
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

        # Set default role
        role_investor = Role.query.filter_by(name='Investor').first()
        if not role_investor:
            role_investor = None

        ver_code = ''.join(random.choices(string.digits, k=6))
        
        # Check referral code
        ref_code = request.form.get('referral_code') or session.get('ref_code')
        referrer_id = None
        if ref_code:
            ref_user = User.query.filter_by(referral_code=ref_code).first()
            if ref_user: 
                referrer_id = ref_user.id

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

@auth_bp.route('/forgot-password')
def forgot_password(): 
    return render_template('forgot-password.html')