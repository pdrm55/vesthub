from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, or_, case, desc
from datetime import datetime, timedelta
from extensions import db
from models import User, Role, Transaction, KYCRequest, Ticket, TicketMessage, SystemSetting, InvestmentPlan, AuditLog, Investment
from decorators import permission_required
from utils import log_admin_activity, set_setting
from tasks import run_profit_distribution

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.role: 
        return redirect(url_for('main.home'))
    return render_template('admin_dashboard.html')

# --- Role Management ---
@admin_bp.route('/roles', methods=['GET', 'POST'])
@login_required
@permission_required('manage_roles')
def roles():
    PERMISSIONS = {
        'manage_users': 'Manage Users',
        'manage_plans': 'Manage Plans',
        'view_ledger': 'View Ledger',
        'manage_payments': 'Manage Payments',
        'manage_withdrawals': 'Manage Withdrawals',
        'manage_tickets': 'Manage Tickets',
        'manage_kyc': 'Manage KYC',
        'manage_settings': 'System Settings',
        'manage_roles': 'Manage Roles',
        'view_logs': 'View Logs'
    }
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            desc = request.form.get('description')
            perms_list = request.form.getlist('permissions')
            perms_str = ",".join(perms_list)
            
            db.session.add(Role(name=name, description=desc, permissions=perms_str))
            db.session.commit()
            
            log_admin_activity('Create Role', f'Created role: {name}')
            flash('New role created successfully.', 'success')
        except Exception as e:
            flash(f'Error creating role: {str(e)}', 'danger')
            
        return redirect(url_for('admin.roles'))
        
    return render_template('admin_roles.html', roles=Role.query.all(), all_permissions=PERMISSIONS)

@admin_bp.route('/roles/edit/<int:role_id>', methods=['POST'])
@login_required
@permission_required('manage_roles')
def edit_role(role_id):
    role = Role.query.get_or_404(role_id)
    if role.name == 'Admin':
        flash('Super Admin role cannot be edited.', 'warning')
        return redirect(url_for('admin.roles'))
        
    role.name = request.form.get('name')
    role.description = request.form.get('description')
    role.permissions = ",".join(request.form.getlist('permissions'))
    
    db.session.commit()
    log_admin_activity('Edit Role', f'Edited role: {role.name}')
    flash('Role updated successfully.', 'success')
    return redirect(url_for('admin.roles'))

@admin_bp.route('/roles/delete/<int:role_id>', methods=['POST'])
@login_required
@permission_required('manage_roles')
def delete_role(role_id):
    role = Role.query.get_or_404(role_id)
    if role.name == 'Admin' or role.users:
        flash('This role cannot be deleted (system role or has assigned users).', 'danger')
    else:
        db.session.delete(role)
        db.session.commit()
        log_admin_activity('Delete Role', f'Deleted role: {role.name}')
        flash('Role deleted successfully.', 'success')
    return redirect(url_for('admin.roles'))

# --- User Management ---
@admin_bp.route('/users')
@login_required
@permission_required('manage_users')
def users():
    return render_template('admin_users.html', users=User.query.all(), roles=Role.query.all())

@admin_bp.route('/users/change-role/<int:user_id>', methods=['POST'])
@login_required
@permission_required('manage_users')
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot change your own role.', 'warning')
    else:
        user.role_id = request.form.get('new_role_id')
        db.session.commit()
        log_admin_activity('Change Role', f'Changed role for user ID {user.id}')
        flash('User role updated.', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@permission_required('manage_users')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.users'))

    try:
        db.session.delete(user)
        db.session.commit()
        log_admin_activity('Delete User', f'Deleted user: {user.email}')
        flash('User deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting user. They may have related records (investments, etc.).', 'danger')
    return redirect(url_for('admin.users'))

# --- Plans Management ---
@admin_bp.route('/plans', methods=['GET', 'POST'])
@login_required
@permission_required('manage_plans')
def plans():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            duration = int(request.form.get('duration'))
            rate = Decimal(request.form.get('rate'))
            desc = request.form.get('description')
            risk = request.form.get('risk_level')

            new_plan = InvestmentPlan(
                name=name, 
                duration_months=duration, 
                annual_return_rate=rate,
                description=desc,
                risk_level=risk
            )
            db.session.add(new_plan)
            db.session.commit()
            
            log_admin_activity('Create Plan', f'Created plan: {name} ({rate}%)')
            flash('Investment plan created successfully.', 'success')
        except Exception as e:
            flash(f'Error creating plan: {str(e)}', 'danger')
            
    return render_template('admin_plans.html', plans=InvestmentPlan.query.all())

@admin_bp.route('/plans/edit/<int:plan_id>', methods=['POST'])
@login_required
@permission_required('manage_plans')
def edit_plan(plan_id):
    plan = InvestmentPlan.query.get_or_404(plan_id)
    try:
        plan.name = request.form.get('name')
        plan.duration_months = int(request.form.get('duration'))
        plan.annual_return_rate = Decimal(request.form.get('rate'))
        plan.description = request.form.get('description')
        plan.risk_level = request.form.get('risk_level')
        db.session.commit()
        log_admin_activity('Edit Plan', f'Edited plan: {plan.name}')
        flash('Plan updated successfully.', 'success')
    except Exception as e:
        flash(f'Error updating plan: {str(e)}', 'danger')
    return redirect(url_for('admin.plans'))

@admin_bp.route('/plans/delete/<int:plan_id>', methods=['POST'])
@login_required
@permission_required('manage_plans')
def delete_plan(plan_id):
    plan = InvestmentPlan.query.get_or_404(plan_id)
    if plan.investments:
        flash('Cannot delete plan with active investments. Deactivate it instead.', 'warning')
    else:
        db.session.delete(plan)
        db.session.commit()
        log_admin_activity('Delete Plan', f'Deleted plan: {plan.name}')
        flash('Plan deleted successfully.', 'success')
    return redirect(url_for('admin.plans'))

@admin_bp.route('/plans/deactivate/<int:plan_id>', methods=['POST'])
@login_required
@permission_required('manage_plans')
def deactivate_plan(plan_id):
    plan = InvestmentPlan.query.get_or_404(plan_id)
    plan.is_active = False
    db.session.commit()
    flash('Plan deactivated.', 'success')
    return redirect(url_for('admin.plans'))

@admin_bp.route('/plans/activate/<int:plan_id>', methods=['POST'])
@login_required
@permission_required('manage_plans')
def activate_plan(plan_id):
    plan = InvestmentPlan.query.get_or_404(plan_id)
    plan.is_active = True
    db.session.commit()
    flash('Plan activated.', 'success')
    return redirect(url_for('admin.plans'))

# --- Finance Management ---
@admin_bp.route('/payments')
@login_required
@permission_required('manage_payments')
def payments():
    pending_payments = Transaction.query.filter_by(type='deposit', status='pending').order_by(Transaction.timestamp.desc()).all()
    return render_template('admin_payments.html', payments=pending_payments)

@admin_bp.route('/payments/approve/<int:tx_id>', methods=['POST'])
@login_required
@permission_required('manage_payments')
def approve_payment(tx_id):
    tx = db.session.get(Transaction, tx_id)
    if tx and tx.status == 'pending':
        tx.status = 'completed'
        
        # Activate associated investment if exists
        if tx.investment:
            tx.investment.status = 'active'
            tx.investment.start_date = datetime.utcnow()
        else:
            # Fallback: Try to find investment by TxID if not directly linked
            inv = Investment.query.filter_by(payment_tx_id=tx.tx_hash).first()
            if inv and inv.status == 'pending_payment':
                inv.status = 'active'
                inv.start_date = datetime.utcnow()
                tx.investment = inv # Link them for future
        
        db.session.commit()
        log_admin_activity('Approve Payment', f'Approved TX {tx.id}')
        flash('Payment approved successfully.', 'success')
    return redirect(url_for('admin.payments'))

@admin_bp.route('/payments/reject/<int:tx_id>', methods=['POST'])
@login_required
@permission_required('manage_payments')
def reject_payment(tx_id):
    tx = db.session.get(Transaction, tx_id)
    if tx and tx.status == 'pending':
        tx.status = 'rejected'

        # Reject associated investment if it exists
        if tx.investment:
            tx.investment.status = 'rejected'
        else:
            # Fallback for older, unlinked transactions
            inv = Investment.query.filter_by(payment_tx_id=tx.tx_hash).first()
            if inv and inv.status == 'pending_payment':
                inv.status = 'rejected'

        db.session.commit()
        log_admin_activity('Reject Payment', f'Rejected TX {tx.id}')
        flash('Payment rejected.', 'warning')
    return redirect(url_for('admin.payments'))

@admin_bp.route('/withdrawals')
@login_required
@permission_required('manage_withdrawals')
def withdrawals():
    pending_withdrawals = Transaction.query.filter_by(type='withdrawal', status='pending').order_by(Transaction.timestamp.desc()).all()
    return render_template('admin_withdrawals.html', requests=pending_withdrawals)

@admin_bp.route('/withdrawals/approve/<int:tx_id>', methods=['POST'])
@login_required
@permission_required('manage_withdrawals')
def approve_withdrawal(tx_id):
    tx = db.session.get(Transaction, tx_id)
    if tx:
        tx.status = 'completed'
        db.session.commit()
        log_admin_activity('Approve Withdrawal', f'Approved WD {tx.id}')
        flash('Withdrawal approved.', 'success')
    return redirect(url_for('admin.withdrawals'))

@admin_bp.route('/withdrawals/reject/<int:tx_id>', methods=['POST'])
@login_required
@permission_required('manage_withdrawals')
def reject_withdrawal(tx_id):
    tx = db.session.get(Transaction, tx_id)
    if tx:
        tx.status = 'rejected'
        db.session.commit()
        log_admin_activity('Reject Withdrawal', f'Rejected WD {tx.id}')
        flash('Withdrawal rejected.', 'warning')
    return redirect(url_for('admin.withdrawals'))

# --- KYC Management ---
@admin_bp.route('/kyc')
@login_required
@permission_required('manage_kyc')
def kyc():
    pending = KYCRequest.query.filter_by(status='pending').all()
    history = KYCRequest.query.filter(KYCRequest.status != 'pending').order_by(KYCRequest.submitted_at.desc()).limit(50).all()
    return render_template('admin_kyc.html', pending=pending, history=history)

@admin_bp.route('/kyc/approve/<int:req_id>', methods=['POST'])
@login_required
@permission_required('manage_kyc')
def approve_kyc(req_id):
    req = db.session.get(KYCRequest, req_id)
    req.status = 'approved'
    req.user.kyc_status = 'verified'
    db.session.commit()
    log_admin_activity('Approve KYC', f'Approved KYC for {req.user.email}')
    return redirect(url_for('admin.kyc'))

@admin_bp.route('/kyc/reject/<int:req_id>', methods=['POST'])
@login_required
@permission_required('manage_kyc')
def reject_kyc(req_id):
    req = db.session.get(KYCRequest, req_id)
    req.status = 'rejected'
    req.user.kyc_status = 'rejected'
    db.session.commit()
    log_admin_activity('Reject KYC', f'Rejected KYC for {req.user.email}')
    return redirect(url_for('admin.kyc'))

# --- Support ---
@admin_bp.route('/support')
@login_required
@permission_required('manage_tickets')
def support():
    tickets = Ticket.query.order_by(Ticket.updated_at.desc()).all()
    return render_template('admin_support.html', open_tickets=tickets, closed_tickets=[])

@admin_bp.route('/support/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
@permission_required('manage_tickets')
def ticket_view(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if request.method == 'POST':
        db.session.add(TicketMessage(
            ticket_id=ticket.id, 
            sender_type='admin', 
            message=request.form.get('message')
        ))
        ticket.status = 'answered'
        ticket.updated_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for('admin.ticket_view', ticket_id=ticket.id))
    return render_template('admin_support_view.html', ticket=ticket)

# ==========================================
# System Settings (FIXED: Added all wallet types)
# ==========================================
@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@permission_required('manage_settings')
def settings():
    # دیکشنری تنظیمات فعلی را از دیتابیس می‌خوانیم تا در فرم نمایش دهیم
    if request.method == 'POST':
        # لیست کامل کلیدهای ولت‌ها و تنظیمات
        keys = [
            'wallet_trc20', 'wallet_erc20', 'wallet_bep20', 'wallet_polygon', 
            'bank_details', 'referral_percentage'
        ]
        for k in keys:
            set_setting(k, request.form.get(k))
            
        log_admin_activity('Update Settings', 'Updated system settings')
        flash('Settings saved successfully.', 'success')
    
    # برای نمایش مقادیر فعلی در فرم
    current_settings = {
        'wallet_trc20': db.session.get(SystemSetting, 'wallet_trc20'),
        'wallet_erc20': db.session.get(SystemSetting, 'wallet_erc20'),
        'wallet_bep20': db.session.get(SystemSetting, 'wallet_bep20'),
        'wallet_polygon': db.session.get(SystemSetting, 'wallet_polygon'),
        'bank_details': db.session.get(SystemSetting, 'bank_details'),
        'referral_percentage': db.session.get(SystemSetting, 'referral_percentage')
    }
    # تبدیل آبجکت‌ها به مقدار (value)
    config = {k: (v.value if v else '') for k, v in current_settings.items()}
    
    return render_template('admin_settings.html', config=config)

# --- Logs & Accounting ---
@admin_bp.route('/logs')
@login_required
@permission_required('view_logs')
def logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('admin_logs.html', logs=logs)

@admin_bp.route('/accounting')
@login_required
@permission_required('view_ledger')
def accounting():
    tab = request.args.get('tab', 'cash_flow')
    
    # Common Filters
    search = request.args.get('search')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    start_date = None
    end_date = None
    
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(hours=23, minutes=59, seconds=59)

    # Initialize variables
    pagination = None
    transactions = None
    profit_logs = None
    total_deposits = 0
    total_withdrawals = 0
    is_detailed_view = False
    users = User.query.with_entities(User.id, User.email).order_by(User.email.asc()).all()

    if tab == 'cash_flow':
        # Mode 1: Cash Flow (Deposits & Withdrawals)
        query = Transaction.query.join(User).filter(Transaction.type.in_(['deposit', 'withdrawal']))
        
        if search:
            search_condition = or_(
                User.email.ilike(f'%{search}%'),
                Transaction.tx_hash.ilike(f'%{search}%'),
                Transaction.description.ilike(f'%{search}%')
            )
            if search.isdigit():
                search_condition = or_(search_condition, Transaction.id == int(search))
            query = query.filter(search_condition)
        
        if start_date:
            query = query.filter(Transaction.timestamp >= start_date)
        if end_date:
            query = query.filter(Transaction.timestamp <= end_date)
            
        # Calculate Totals
        total_deposits = query.with_entities(func.sum(Transaction.amount)).filter(
            Transaction.type == 'deposit', Transaction.status == 'completed'
        ).scalar() or 0
        
        total_withdrawals = query.with_entities(func.sum(Transaction.amount)).filter(
            Transaction.type == 'withdrawal', Transaction.status == 'completed'
        ).scalar() or 0
        
        page = request.args.get('page', 1, type=int)
        pagination = query.order_by(Transaction.timestamp.desc()).paginate(page=page, per_page=20, error_out=False)
        transactions = pagination.items

    elif tab == 'profit_logs':
        user_id = request.args.get('user_id')
        
        if user_id:
            # Scenario A: Detailed View for specific user
            is_detailed_view = True
            query = Transaction.query.filter(
                Transaction.user_id == user_id,
                Transaction.type.in_(['profit', 'referral_bonus'])
            )
            
            if start_date:
                query = query.filter(Transaction.timestamp >= start_date)
            if end_date:
                query = query.filter(Transaction.timestamp <= end_date)
                
            profit_logs = query.order_by(Transaction.timestamp.desc()).all()
        else:
            # Scenario B: Aggregate View (Default)
            query = db.session.query(
                func.date(Transaction.timestamp).label('day'),
                func.count(Transaction.id).label('daily_count'),
                func.sum(Transaction.amount).label('daily_total'),
                func.sum(case((Transaction.type == 'profit', Transaction.amount), else_=0)).label('profit_sum'),
                func.sum(case((Transaction.type == 'referral_bonus', Transaction.amount), else_=0)).label('ref_sum')
            ).filter(
                Transaction.type.in_(['profit', 'referral_bonus'])
            )
            
            if start_date:
                query = query.filter(Transaction.timestamp >= start_date)
            if end_date:
                query = query.filter(Transaction.timestamp <= end_date)
                
            profit_logs = query.group_by(func.date(Transaction.timestamp))\
                               .order_by(desc('day')).all()

    return render_template(
        'admin_accounting.html',
        tab=tab,
        pagination=pagination,
        transactions=transactions,
        profit_logs=profit_logs,
        total_deposits=total_deposits,
        total_withdrawals=total_withdrawals,
        search=search,
        start_date=start_date_str,
        end_date=end_date_str,
        users=users,
        is_detailed_view=is_detailed_view
    )

# --- Test Route ---
@admin_bp.route('/test/distribute-profit', methods=['POST'])
@login_required
@permission_required('manage_settings')
def distribute_test_profit():
    count = run_profit_distribution(current_app._get_current_object())
    log_admin_activity('Distribute Profit', f'Manual run: {count} payouts')
    flash(f'Manual profit distribution completed. {count} payouts.', 'success')
    return redirect(url_for('admin.accounting'))

@admin_bp.route('/api/chart/admin-stats')
@login_required
def api_admin_stats():
    # آمار ثبت‌نام کاربران در ۷ روز گذشته
    today = datetime.utcnow().date()
    labels = []
    data_users = []
    
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        # شمارش کاربران ثبت‌نام شده در آن روز
        count = User.query.filter(db.func.date(User.created_at) == d).count()
        labels.append(d.strftime('%d %b'))
        data_users.append(count)
        
    return jsonify({
        'registrations': {
            'labels': labels,
            'data': data_users
        }
    })