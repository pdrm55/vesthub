import random
import string
import pyotp
from decimal import Decimal
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, current_app, send_from_directory
from flask_login import login_required, current_user
from extensions import db
from models import Investment, InvestmentPlan, Transaction, Ticket, TicketMessage, KYCRequest, User
from utils import get_withdrawable_balance, get_setting, save_uploaded_file, send_system_email

user_bp = Blueprint('user', __name__)

@user_bp.route('/dashboard')
@login_required
def dashboard():
    total_invested = sum(inv.amount for inv in current_user.investments if inv.status == 'active')
    total_profit = get_withdrawable_balance(current_user.id)
    referral_count = len(current_user.referrals)
    
    referral_earnings = db.session.query(db.func.sum(Transaction.amount)).filter_by(
        user_id=current_user.id, type='referral_bonus', status='completed'
    ).scalar() or Decimal('0.0')
    
    return render_template('dashboard.html', 
                           user=current_user, 
                           total_invested=total_invested, 
                           total_profit=total_profit, 
                           referral_count=referral_count, 
                           referral_earnings=referral_earnings, 
                           active_investments=current_user.investments)

@user_bp.route('/invest-plans')
@login_required
def invest_plans():
    if current_user.risk_profile == 'not_assessed': 
        flash('Please complete the risk assessment first.', 'warning')
        return redirect(url_for('user.risk_assessment'))
    
    base_query = InvestmentPlan.query.filter_by(is_active=True).order_by(InvestmentPlan.duration_months.desc())
    
    if current_user.risk_profile == 'conservative': 
        plans = base_query.filter(InvestmentPlan.risk_level == 'low').all()
    elif current_user.risk_profile == 'balanced': 
        plans = base_query.filter(InvestmentPlan.risk_level.in_(['low', 'medium'])).all()
    else: 
        plans = base_query.all()
        
    return render_template('invest-plans.html', plans=plans)

@user_bp.route('/create-investment', methods=['POST'])
@login_required
def create_investment():
    plan_id = request.form.get('plan_id')
    amount_str = request.form.get('amount')
    try:
        amount = Decimal(amount_str)
        if amount <= 0: raise ValueError
    except:
        flash('Invalid amount.', 'danger')
        return redirect(url_for('user.invest_plans'))

    new_inv = Investment(
        user_id=current_user.id, 
        plan_id=plan_id, 
        amount=amount, 
        status='pending_payment', 
        start_date=datetime.utcnow()
    )
    db.session.add(new_inv)
    db.session.commit()
    return redirect(url_for('user.investment_pending', investment_id=new_inv.id))

@user_bp.route('/invest/pending/<int:investment_id>')
@login_required
def investment_pending(investment_id):
    inv = Investment.query.get_or_404(investment_id)
    if inv.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('user.dashboard'))
    
    wallets = {
        'trc20': get_setting('wallet_trc20'), 
        'erc20': get_setting('wallet_erc20'), 
        'bep20': get_setting('wallet_bep20'), 
        'polygon': get_setting('wallet_polygon'), 
        'bank': get_setting('bank_details')
    }
    return render_template('investment_pending.html', investment=inv, wallets=wallets)

@user_bp.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@user_bp.route('/invest/submit-proof/<int:investment_id>', methods=['POST'])
@login_required
def submit_proof(investment_id):
    inv = Investment.query.get_or_404(investment_id)
    if inv.user_id != current_user.id: return redirect(url_for('user.dashboard'))
        
    tx_hash = request.form.get('txnHash')
    
    file = request.files.get('proofFile')
    has_file = file and file.filename != ''

    if not tx_hash and not has_file:
        flash('Please provide either a TxID or a proof document.', 'danger')
        return redirect(url_for('user.investment_pending', investment_id=investment_id))

    if not tx_hash and has_file:
        tx_hash = f"DOC-{int(datetime.utcnow().timestamp())}"

    inv.payment_tx_id = tx_hash
    
    if has_file:
        filename = save_uploaded_file(file)
        if filename:
            inv.payment_proof_url = filename
    
    db.session.add(Transaction(
        user_id=current_user.id, 
        type='deposit', 
        amount=inv.amount, 
        status='pending', 
        tx_hash=tx_hash,
        description=f"Deposit for plan #{inv.plan_id}",
        investment_id=inv.id
    ))
    db.session.commit()
    flash('Payment proof submitted and awaiting approval.', 'success')
    return redirect(url_for('user.dashboard'))

@user_bp.route('/payment/process/<int:investment_id>', methods=['POST'])
@login_required
def process_online_payment(investment_id):
    inv = Investment.query.get_or_404(investment_id)
    if inv.user_id != current_user.id: return redirect(url_for('user.dashboard'))

    inv.status = 'active'
    inv.start_date = datetime.utcnow()
    inv.payment_tx_id = f"ONLINE-{random.randint(1000,9999)}"
    
    db.session.add(Transaction(
        user_id=current_user.id, 
        type='deposit', 
        amount=inv.amount, 
        status='completed', 
        tx_hash=inv.payment_tx_id,
        description="Online Payment Gateway",
        investment_id=inv.id
    ))
    db.session.commit()
    flash('Online payment processed successfully.', 'success')
    return redirect(url_for('user.dashboard'))

@user_bp.route('/investment/delete/<int:investment_id>', methods=['POST'])
@login_required
def delete_investment(investment_id):
    inv = Investment.query.get_or_404(investment_id)
    
    if inv.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('user.dashboard'))
        
    if inv.status == 'pending_payment':
        try:
            db.session.delete(inv)
            db.session.commit()
            flash('Investment request cancelled successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error cancelling investment.', 'danger')
    else:
        flash('Cannot cancel active or processed investments.', 'warning')
        
    return redirect(url_for('user.dashboard'))

@user_bp.route('/withdrawal', methods=['GET', 'POST'])
@login_required
def withdrawal():
    if current_user.kyc_status != 'verified': 
        flash('Please complete your Identity Verification (KYC) before making a withdrawal.', 'warning')
        return redirect(url_for('user.settings'))
        
    # بررسی فعال بودن 2FA
    if not current_user.is_2fa_enabled:
        flash('Please enable Two-Factor Authentication (2FA) in Settings to request withdrawals.', 'warning')
        return redirect(url_for('user.settings'))
    
    available = get_withdrawable_balance(current_user.id)
    history = Transaction.query.filter_by(user_id=current_user.id, type='withdrawal').order_by(Transaction.timestamp.desc()).all()
    
    # --- STEP 2: VERIFICATION & CONFIRMATION ---
    if request.method == 'POST' and 'verify_withdrawal' in request.form:
        pending_data = session.get('pending_withdrawal')
        if not pending_data:
            flash('Withdrawal session expired. Please try again.', 'danger')
            return redirect(url_for('user.withdrawal'))
            
        email_code_input = request.form.get('email_code')
        ga_code_input = request.form.get('ga_code')
        
        # 1. Validate Email Code
        if email_code_input != pending_data['code']:
            flash('Invalid Email Verification Code.', 'danger')
            return render_template('withdrawal.html', available_balance=available, locked_balance=Decimal('0'), history=history, verify_mode=True)
            
        # 2. Validate Google Authenticator Code
        if not pyotp.TOTP(current_user.two_factor_secret).verify(ga_code_input):
            flash('Invalid Google Authenticator Code.', 'danger')
            return render_template('withdrawal.html', available_balance=available, locked_balance=Decimal('0'), history=history, verify_mode=True)
            
        # 3. Process Withdrawal
        try:
            amt = Decimal(pending_data['amount'])
            # Re-check balance (concurrency check)
            user = db.session.query(User).filter(User.id == current_user.id).with_for_update().one()
            current_available = get_withdrawable_balance(user.id)
            
            if amt <= current_available:
                db.session.add(Transaction(user_id=user.id, type='withdrawal', amount=amt, status='pending', description='User withdrawal request'))
                db.session.commit()
                session.pop('pending_withdrawal', None) # Clear session
                flash('Withdrawal request submitted successfully.', 'success')
                return redirect(url_for('user.withdrawal'))
            else:
                db.session.rollback()
                flash('Insufficient balance.', 'danger')
                session.pop('pending_withdrawal', None)
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'danger')
        return redirect(url_for('user.withdrawal'))

    # --- STEP 1: REQUEST & SEND EMAIL ---
    if request.method == 'POST':
        try:
            amt = Decimal(request.form.get('amount'))
            if amt <= 0: raise ValueError
            
            if amt > available:
                flash('Insufficient balance.', 'danger')
                return redirect(url_for('user.withdrawal'))
                
            # Generate 6-digit Email Code
            email_code = ''.join(random.choices(string.digits, k=6))
            
            # Store in Session
            session['pending_withdrawal'] = {
                'amount': str(amt),
                'code': email_code,
                'timestamp': datetime.utcnow().timestamp()
            }
            
            # Send Email
            send_system_email(
                "Withdrawal Verification", 
                current_user.email, 
                f"Your withdrawal verification code is: {email_code}. Do not share this code."
            )
            
            flash('Verification code sent to your email. Please enter it below along with your 2FA code.', 'info')
            return render_template('withdrawal.html', available_balance=available, locked_balance=Decimal('0'), history=history, verify_mode=True)

        except:
            flash('Invalid amount entered.', 'danger')
            return redirect(url_for('user.withdrawal'))

    return render_template('withdrawal.html', available_balance=available, locked_balance=Decimal('0'), history=history, verify_mode=False)

@user_bp.route('/wallet', methods=['GET', 'POST'])
@login_required
def wallet():
    if request.method == 'POST': 
        current_user.wallet_network = request.form.get('wallet_type')
        current_user.wallet_address = request.form.get('wallet_address')
        db.session.commit()
        flash('Wallet information saved.', 'success')
        
    company_wallets = {
        'trc20': get_setting('wallet_trc20'), 
        'erc20': get_setting('wallet_erc20'), 
        'bep20': get_setting('wallet_bep20'), 
        'polygon': get_setting('wallet_polygon')
    }
    
    return render_template('wallet.html', user=current_user, company_wallets=company_wallets)

@user_bp.route('/settings', methods=['GET'])
@login_required
def settings():
    kyc_req = KYCRequest.query.filter_by(user_id=current_user.id).first()
    return render_template('settings.html', user=current_user, kyc_request=kyc_req)

@user_bp.route('/settings/enable-2fa', methods=['POST'])
@login_required
def enable_2fa():
    secret = pyotp.random_base32()
    current_user.two_factor_secret = secret
    db.session.commit()
    return jsonify({'secret': secret, 'uri': pyotp.totp.TOTP(secret).provisioning_uri(name=current_user.email, issuer_name='VestHub')})

@user_bp.route('/settings/confirm-2fa', methods=['POST'])
@login_required
def confirm_2fa():
    code = request.form.get('code')
    if current_user.two_factor_secret and pyotp.TOTP(current_user.two_factor_secret).verify(code): 
        current_user.is_2fa_enabled = True
        db.session.commit()
        flash('Two-factor authentication enabled.', 'success')
    else: 
        flash('Incorrect code.', 'danger')
    return redirect(url_for('user.settings'))

@user_bp.route('/settings/submit-kyc', methods=['POST'])
@login_required
def submit_kyc():
    id_f = request.files.get('idDoc')
    ad_f = request.files.get('addressDoc')
    if id_f and ad_f:
        id_path = save_uploaded_file(id_f)
        ad_path = save_uploaded_file(ad_f)
        if id_path and ad_path:
            current_user.kyc_status = 'pending'
            old_req = KYCRequest.query.filter_by(user_id=current_user.id).first()
            if old_req: db.session.delete(old_req)
            db.session.add(KYCRequest(user_id=current_user.id, id_document_url=id_path, address_document_url=ad_path, status='pending'))
            db.session.commit()
            flash('Documents submitted and are pending review.', 'success')
        else:
            flash('Invalid file or format detected.', 'danger')
    return redirect(url_for('user.settings'))

@user_bp.route('/risk-assessment', methods=['GET', 'POST'])
@login_required
def risk_assessment():
    if request.method == 'POST':
        try:
            # محاسبه واقعی امتیاز ریسک
            total_score = 0
            # جمع‌آوری امتیازات از 15 سوال
            for i in range(1, 16):
                val = request.form.get(f'q{i}')
                if val and val.isdigit():
                    total_score += int(val)
            
            # تعیین پروفایل بر اساس مجموع امتیازات
            profile = 'conservative'
            if total_score >= 80:
                profile = 'aggressive'
            elif total_score >= 50:
                profile = 'balanced'
            
            current_user.risk_score = total_score
            current_user.risk_profile = profile
            db.session.commit()
            
            flash(f'Assessment Complete! Your risk profile is: {profile.title()}', 'success')
            return redirect(url_for('user.dashboard'))
            
        except Exception as e:
            # لاگ خطا برای دیباگ
            print(f"Error in risk assessment: {e}")
            flash('An error occurred during calculation. Please try again.', 'danger')
            
    return render_template('risk_assessment.html')

@user_bp.route('/support', methods=['GET', 'POST'])
@login_required
def support():
    if request.method == 'POST':
        tk = Ticket(user_id=current_user.id, subject=request.form.get('subject'), category=request.form.get('category'), status='open')
        db.session.add(tk)
        db.session.commit()
        msg = TicketMessage(ticket_id=tk.id, sender_type='user', message=request.form.get('message'))
        db.session.add(msg)
        db.session.commit()
        flash('New ticket created.', 'success')
        return redirect(url_for('user.support'))
    tickets = Ticket.query.filter_by(user_id=current_user.id).order_by(Ticket.updated_at.desc()).all()
    return render_template('support.html', tickets=tickets)

@user_bp.route('/support/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def ticket_view(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if ticket.user_id != current_user.id: return redirect(url_for('user.support'))
    if request.method == 'POST':
        db.session.add(TicketMessage(ticket_id=ticket.id, sender_type='user', message=request.form.get('message')))
        ticket.status = 'open'
        ticket.updated_at = datetime.utcnow()
        db.session.commit()
    return render_template('support_view.html', ticket=ticket)

@user_bp.route('/api/chart/user-data')
@login_required
def api_user_data():
    # محاسبه مجموع سرمایه‌گذاری‌های فعال
    total_invested = sum(inv.amount for inv in current_user.investments if inv.status == 'active')
    
    # محاسبه سود قابل برداشت
    total_profit = get_withdrawable_balance(current_user.id)
    
    # محاسبه درآمد حاصل از رفرال
    referral_earnings = db.session.query(db.func.sum(Transaction.amount)).filter_by(
        user_id=current_user.id, type='referral_bonus', status='completed'
    ).scalar() or Decimal('0.0')

    # داده‌های نمودار رشد (۷ روز گذشته)
    today = datetime.utcnow().date()
    growth_labels = []
    growth_data = []
    
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        # محاسبه سود روزانه
        daily_sum = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == 'profit',
            db.func.date(Transaction.timestamp) == d
        ).scalar() or Decimal('0.0')
        
        growth_labels.append(d.strftime('%d %b')) # نمونه: 12 Dec
        growth_data.append(float(daily_sum))

    return jsonify({
        'assets': {
            'invested': float(total_invested), 
            'profit': float(total_profit), 
            'referral': float(referral_earnings)
        },
        'growth': {
            'labels': growth_labels,
            'data': growth_data
        }
    })