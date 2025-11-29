import random
import pyotp
from decimal import Decimal
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Investment, InvestmentPlan, Transaction, Ticket, TicketMessage, KYCRequest, User
from utils import get_withdrawable_balance, get_setting, save_uploaded_file

user_bp = Blueprint('user', __name__)

@user_bp.route('/dashboard')
@login_required
def dashboard():
    # Sum using Python sum() on Decimals works correctly
    total_invested = sum(inv.amount for inv in current_user.investments if inv.status in ['active', 'pending_payment'])
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
        flash('Please complete the risk assessment first.', 'info')
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
    """
    Creates a new investment record from a selected plan and amount.
    - Sets the initial status to 'pending_payment'.
    """
    plan_id = request.form.get('plan_id')
    amount_str = request.form.get('amount')
    
    try:
        amount = Decimal(amount_str)
        if amount <= 0: raise ValueError
    except:
        flash('Invalid amount.', 'danger')
        return redirect(url_for('user.invest_plans'))

    # Create the new investment object.
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
    """
    Displays the payment page for a pending investment.
    - Shows company wallet addresses for manual payment.
    """
    inv = Investment.query.get_or_404(investment_id)
    if inv.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('user.dashboard'))
        
    # Fetch wallet details from system settings.
    wallets = {
        'trc20': get_setting('wallet_trc20'), 
        'erc20': get_setting('wallet_erc20'), 
        'bep20': get_setting('wallet_bep20'), 
        'polygon': get_setting('wallet_polygon'), 
        'bank': get_setting('bank_details')
    }
    return render_template('investment_pending.html', investment=inv, wallets=wallets)

@user_bp.route('/invest/submit-proof/<int:investment_id>', methods=['POST'])
@login_required
def submit_proof(investment_id):
    """
    Submits the transaction hash/ID as proof of payment for a manual deposit.
    - Creates a 'deposit' transaction with 'pending' status for admin approval.
    """
    inv = Investment.query.get_or_404(investment_id)
    if inv.user_id != current_user.id:
        return redirect(url_for('user.dashboard'))
        
    tx_hash = request.form.get('txnHash')
    inv.payment_tx_id = tx_hash
    
    # Create a corresponding transaction record.
    db.session.add(Transaction(
        user_id=current_user.id, 
        type='deposit', 
        amount=inv.amount, 
        status='pending', 
        tx_hash=tx_hash,
        description=f"Deposit for plan #{inv.plan_id}"
    ))
    db.session.commit()
    flash('Payment proof submitted and awaiting approval.', 'success')
    return redirect(url_for('user.dashboard'))

@user_bp.route('/payment/process/<int:investment_id>', methods=['POST'])
@login_required
def process_online_payment(investment_id):
    """
    (Placeholder) Simulates processing an online payment.
    - Activates the investment and creates a 'completed' deposit transaction.
    """
    inv = Investment.query.get_or_404(investment_id)
    if inv.user_id != current_user.id: return redirect(url_for('user.dashboard'))

    inv.status = 'active'
    inv.start_date = datetime.utcnow()
    inv.payment_tx_id = f"ONLINE-{random.randint(1000,9999)}"
    
    # Create a completed transaction record for the online payment.
    db.session.add(Transaction(
        user_id=current_user.id, 
        type='deposit', 
        amount=inv.amount, 
        status='completed', 
        tx_hash=inv.payment_tx_id,
        description="Online Payment Gateway"
    ))
    db.session.commit()
    flash('Online payment processed successfully.', 'success')
    return redirect(url_for('user.dashboard'))

@user_bp.route('/withdrawal', methods=['GET', 'POST'])
@login_required
def withdrawal():
    """
    Handles withdrawal requests.
    - Requires KYC verification.
    - On POST, creates a 'withdrawal' transaction with 'pending' status.
    """
    if current_user.kyc_status != 'verified': 
        flash('You must complete KYC verification before withdrawing funds.', 'warning')
        return redirect(url_for('user.settings'))
    
    available = get_withdrawable_balance(current_user.id)
    
    if request.method == 'POST':
        try:
            amt = Decimal(request.form.get('amount'))
            if amt <= 0: raise ValueError
        except:
            flash('Invalid amount entered.', 'danger')
            return redirect(url_for('user.withdrawal'))

        # --- RACE CONDITION PREVENTION ---
        # Lock the user's row during the transaction to prevent double-spending.
        try:
            # Note: with_for_update() works on Postgres/MySQL. 
            # On SQLite, it might be ignored, but using a single session transaction helps.
            user = db.session.query(User).filter(User.id == current_user.id).with_for_update().one()
            
            # Re-calculate the available balance inside the locked transaction to get the most current value.
            current_available = get_withdrawable_balance(user.id)
            
            if amt <= current_available:
                db.session.add(Transaction(
                    user_id=user.id, 
                    type='withdrawal', 
                    amount=amt, 
                    status='pending',
                    description='User withdrawal request'
                ))
                db.session.commit()
                flash('Withdrawal request submitted.', 'success')
            else:
                db.session.rollback()
                flash('Insufficient balance.', 'danger')
                
        except Exception as e:
            db.session.rollback()
            print(f"Error in withdrawal: {e}")
            flash('An error occurred. Please try again.', 'danger')
            
        return redirect(url_for('user.withdrawal'))

    history = Transaction.query.filter_by(user_id=current_user.id, type='withdrawal').order_by(Transaction.timestamp.desc()).all()
    return render_template('withdrawal.html', available_balance=available, locked_balance=Decimal('0'), history=history)

@user_bp.route('/wallet', methods=['GET', 'POST'])
@login_required
def wallet():
    """Allows the user to set their withdrawal wallet address and network."""
    if request.method == 'POST': 
        current_user.wallet_network = request.form.get('wallet_type')
        current_user.wallet_address = request.form.get('wallet_address')
        db.session.commit()
        flash('Wallet information saved.', 'success')
    return render_template('wallet.html', user=current_user)

@user_bp.route('/settings', methods=['GET'])
@login_required
def settings():
    """Displays the user settings page, including KYC status and 2FA options."""
    kyc_req = KYCRequest.query.filter_by(user_id=current_user.id).first()
    return render_template('settings.html', user=current_user, kyc_request=kyc_req)

@user_bp.route('/settings/enable-2fa', methods=['POST'])
@login_required
def enable_2fa():
    """Generates a new 2FA secret and provisioning URI for the user to scan."""
    secret = pyotp.random_base32()
    current_user.two_factor_secret = secret
    db.session.commit()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=current_user.email, issuer_name='VestHub')
    return jsonify({'secret': secret, 'uri': uri})

@user_bp.route('/settings/confirm-2fa', methods=['POST'])
@login_required
def confirm_2fa():
    """Confirms and enables 2FA for the user after they enter a valid TOTP code."""
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
    """
    Handles the submission of KYC documents.
    - Saves uploaded files and creates a KYCRequest record with 'pending' status.
    """
    id_f = request.files.get('idDoc')
    ad_f = request.files.get('addressDoc')
    
    if id_f and ad_f:
        id_path = save_uploaded_file(id_f)
        ad_path = save_uploaded_file(ad_f)
        
        if id_path and ad_path:
            current_user.kyc_status = 'pending'
            # Delete any previous, old request to replace it with the new one.
            old_req = KYCRequest.query.filter_by(user_id=current_user.id).first()
            if old_req: db.session.delete(old_req)
            
            db.session.add(KYCRequest(
                user_id=current_user.id, 
                id_document_url=id_path, 
                address_document_url=ad_path, 
                status='pending'
            ))
            db.session.commit()
            flash('Documents submitted and are pending review.', 'success')
        else:
            flash('Invalid file or format detected.', 'danger')
            
    return redirect(url_for('user.settings'))

@user_bp.route('/risk-assessment', methods=['GET', 'POST'])
@login_required
def risk_assessment():
    """
    (Placeholder) A simple risk assessment form.
    - On submission, sets a default risk profile for the user.
    """
    if request.method == 'POST': 
        current_user.risk_profile = 'balanced'
        current_user.risk_score = 50
        db.session.commit()
        flash('Your risk profile has been updated.', 'success')
        return redirect(url_for('user.dashboard'))
    return render_template('risk_assessment.html')

@user_bp.route('/support', methods=['GET', 'POST'])
@login_required
def support():
    """
    Displays the support center and handles new ticket submissions.
    - On POST, creates a new Ticket and its initial TicketMessage.
    """
    if request.method == 'POST':
        tk = Ticket(
            user_id=current_user.id, 
            subject=request.form.get('subject'), 
            category=request.form.get('category'), 
            status='open'
        )
        db.session.add(tk)
        db.session.commit()
        
        msg = TicketMessage(
            ticket_id=tk.id, 
            sender_type='user', 
            message=request.form.get('message')
        )
        db.session.add(msg)
        db.session.commit()
        flash('New ticket created.', 'success')
        return redirect(url_for('user.support'))
        
    tickets = Ticket.query.filter_by(user_id=current_user.id).order_by(Ticket.updated_at.desc()).all()
    return render_template('support.html', tickets=tickets)

@user_bp.route('/support/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def ticket_view(ticket_id):
    """
    Displays a single support ticket and its conversation.
    - On POST, adds a new reply from the user to the ticket.
    """
    ticket = Ticket.query.get_or_404(ticket_id)
    if ticket.user_id != current_user.id:
        return redirect(url_for('user.support'))
        
    if request.method == 'POST':
        # Add the user's message to the ticket.
        db.session.add(TicketMessage(
            ticket_id=ticket.id, 
            sender_type='user', 
            message=request.form.get('message')
        ))
        ticket.status = 'open'
        ticket.updated_at = datetime.utcnow()
        db.session.commit()
        
    return render_template('support_view.html', ticket=ticket)

@user_bp.route('/api/chart/user-data')
@login_required
def api_user_data(): 
    """(Placeholder) API endpoint to provide data for dashboard charts."""
    return jsonify({'assets': {'invested':0, 'profit':0, 'referral':0}})