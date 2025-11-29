from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from extensions import db
from models import User, Role, Transaction, KYCRequest, Ticket, TicketMessage, SystemSetting, InvestmentPlan, AuditLog
from decorators import permission_required
from utils import log_admin_activity, set_setting
from tasks import run_profit_distribution

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """Renders the main admin dashboard."""
    if not current_user.role: 
        return redirect(url_for('main.home'))
    return render_template('admin_dashboard.html')

# --- Role Management ---

@admin_bp.route('/roles', methods=['GET', 'POST'])
@login_required
@permission_required('manage_roles')
def roles():
    """
    Manages user roles and their permissions.
    - On POST, creates a new role with the selected permissions.
    """
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
    
    # Handle form submission for creating a new role.
    if request.method == 'POST':
        name = request.form.get('name')
        desc = request.form.get('description')
        perms_list = request.form.getlist('permissions')
        perms_str = ",".join(perms_list)
        
        db.session.add(Role(name=name, description=desc, permissions=perms_str))
        db.session.commit()
        log_admin_activity('Create Role', f'Created role: {name}')
        flash('New role created successfully.', 'success')
        return redirect(url_for('admin.roles'))
        
    return render_template('admin_roles.html', roles=Role.query.all(), all_permissions=PERMISSIONS)

@admin_bp.route('/roles/edit/<int:role_id>', methods=['POST'])
@login_required
@permission_required('manage_roles')
def edit_role(role_id):
    """Edits an existing role's name, description, and permissions."""
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
    """Deletes a role if it's not a system role and has no assigned users."""
    role = Role.query.get_or_404(role_id)
    if role.name == 'Admin' or role.users:
        flash('This role cannot be deleted (system role or has users).', 'danger')
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
    """Displays a list of all users for management."""
    return render_template('admin_users.html', users=User.query.all(), roles=Role.query.all())

@admin_bp.route('/users/change-role/<int:user_id>', methods=['POST'])
@login_required
@permission_required('manage_users')
def change_role(user_id):
    """Changes the role of a specific user."""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot change your own role.', 'warning')
    else:
        user.role_id = request.form.get('new_role_id')
        db.session.commit()
        log_admin_activity('Change Role', f'Changed role for user ID {user.id}')
        flash('User role updated.', 'success')
    return redirect(url_for('admin.users'))

# --- Finance ---

@admin_bp.route('/payments')
@login_required
@permission_required('manage_payments')
def payments():
    """Displays all deposit transactions for approval or rejection."""
    return render_template('admin_payments.html', payments=Transaction.query.filter_by(type='deposit').order_by(Transaction.timestamp.desc()).all())

@admin_bp.route('/payments/approve/<int:tx_id>', methods=['POST'])
@login_required
@permission_required('manage_payments')
def approve_payment(tx_id):
    """Approves a pending deposit transaction."""
    tx = db.session.get(Transaction, tx_id)
    if tx and tx.status == 'pending':
        tx.status = 'completed'
        db.session.commit()
        log_admin_activity('Approve Payment', f'Approved TX {tx.id}')
        flash('Deposit approved.', 'success')
    return redirect(url_for('admin.payments'))

@admin_bp.route('/payments/reject/<int:tx_id>', methods=['POST'])
@login_required
@permission_required('manage_payments')
def reject_payment(tx_id):
    """Rejects a pending deposit transaction."""
    tx = db.session.get(Transaction, tx_id)
    if tx and tx.status == 'pending':
        tx.status = 'rejected'
        db.session.commit()
        log_admin_activity('Reject Payment', f'Rejected TX {tx.id}')
        flash('Deposit rejected.', 'warning')
    return redirect(url_for('admin.payments'))

@admin_bp.route('/withdrawals')
@login_required
@permission_required('manage_withdrawals')
def withdrawals():
    """Displays all withdrawal requests for approval or rejection."""
    return render_template('admin_withdrawals.html', requests=Transaction.query.filter_by(type='withdrawal').order_by(Transaction.timestamp.desc()).all())

@admin_bp.route('/withdrawals/approve/<int:tx_id>', methods=['POST'])
@login_required
@permission_required('manage_withdrawals')
def approve_withdrawal(tx_id):
    """Approves a pending withdrawal request."""
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
    """Rejects a pending withdrawal request."""
    tx = db.session.get(Transaction, tx_id)
    if tx:
        tx.status = 'rejected'
        db.session.commit()
        log_admin_activity('Reject Withdrawal', f'Rejected WD {tx.id}')
        flash('Withdrawal rejected.', 'warning')
    return redirect(url_for('admin.withdrawals'))

# --- KYC ---

@admin_bp.route('/kyc')
@login_required
@permission_required('manage_kyc')
def kyc():
    """Displays pending and historical KYC requests for review."""
    pending = KYCRequest.query.filter_by(status='pending').all()
    history = KYCRequest.query.filter(KYCRequest.status != 'pending').order_by(KYCRequest.submitted_at.desc()).limit(50).all()
    return render_template('admin_kyc.html', pending=pending, history=history)

@admin_bp.route('/kyc/approve/<int:req_id>', methods=['POST'])
@login_required
@permission_required('manage_kyc')
def approve_kyc(req_id):
    """Approves a KYC request and updates the user's KYC status."""
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
    """Rejects a KYC request and updates the user's KYC status."""
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
    """Displays all support tickets for management."""
    tickets = Ticket.query.order_by(Ticket.updated_at.desc()).all()
    return render_template('admin_support.html', open_tickets=tickets, closed_tickets=[])

@admin_bp.route('/support/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
@permission_required('manage_tickets')
def ticket_view(ticket_id):
    """Displays a single support ticket and allows an admin to reply."""
    ticket = Ticket.query.get_or_404(ticket_id)
    # Handle admin's reply to the ticket.
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

# --- Settings & Plans ---

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@permission_required('manage_settings')
def settings():
    """Manages system-wide settings like wallet addresses and referral percentages."""
    if request.method == 'POST':
        for k in ['wallet_trc20', 'bank_details', 'referral_percentage']:
            set_setting(k, request.form.get(k))
        log_admin_activity('Update Settings', 'Updated system settings')
        flash('Settings saved.', 'success')
    return render_template('admin_settings.html', config={})

@admin_bp.route('/plans', methods=['GET', 'POST'])
@login_required
@permission_required('manage_plans')
def plans():
    """Manages investment plans (create, edit, activate, deactivate)."""
    if request.method == 'POST':
        # Ensure financial rates are handled as Decimal for precision.
        rate = Decimal(request.form.get('rate', 10))
        
        db.session.add(InvestmentPlan(
            name=request.form.get('name'), 
            duration_months=int(request.form.get('duration', 12)), 
            annual_return_rate=rate,
            description=request.form.get('description'),
            risk_level=request.form.get('risk_level', 'low')
        ))
        db.session.commit()
        log_admin_activity('Create Plan', 'Created new investment plan')
        flash('New plan created.', 'success')
    return render_template('admin_plans.html', plans=InvestmentPlan.query.all())

@admin_bp.route('/plans/deactivate/<int:plan_id>', methods=['POST'])
@login_required
@permission_required('manage_plans')
def deactivate_plan(plan_id):
    """Deactivates a plan, making it unavailable for new investments."""
    plan = InvestmentPlan.query.get_or_404(plan_id)
    plan.is_active = False
    db.session.commit()
    log_admin_activity('Deactivate Plan', f'Deactivated plan: {plan.name}')
    flash('Plan deactivated successfully.', 'success')
    return redirect(url_for('admin.plans'))

@admin_bp.route('/plans/activate/<int:plan_id>', methods=['POST'])
@login_required
@permission_required('manage_plans')
def activate_plan(plan_id):
    """Reactivates a previously deactivated plan."""
    plan = InvestmentPlan.query.get_or_404(plan_id)
    plan.is_active = True
    db.session.commit()
    log_admin_activity('Activate Plan', f'Activated plan: {plan.name}')
    flash('Plan activated successfully.', 'success')
    return redirect(url_for('admin.plans'))

@admin_bp.route('/plans/delete/<int:plan_id>', methods=['POST'])
@login_required
@permission_required('manage_plans')
def delete_plan(plan_id):
    """Deletes a plan if it has no associated investments."""
    plan = InvestmentPlan.query.get_or_404(plan_id)
    if plan.investments:
        flash('Cannot delete a plan that has active investments. Deactivate it instead.', 'warning')
    else:
        db.session.delete(plan)
        db.session.commit()
        log_admin_activity('Delete Plan', f'Deleted plan: {plan.name}')
        flash('Plan deleted successfully.', 'success')
    return redirect(url_for('admin.plans'))

@admin_bp.route('/plans/edit/<int:plan_id>', methods=['POST'])
@login_required
@permission_required('manage_plans')
def edit_plan(plan_id):
    """Edits the details of an existing investment plan."""
    plan = InvestmentPlan.query.get_or_404(plan_id)
    
    plan.name = request.form.get('name')
    plan.duration_months = int(request.form.get('duration'))
    plan.annual_return_rate = Decimal(request.form.get('rate'))
    plan.description = request.form.get('description')
    plan.risk_level = request.form.get('risk_level')
    
    db.session.commit()
    log_admin_activity('Edit Plan', f'Edited plan: {plan.name}')
    flash('Plan updated successfully.', 'success')
    return redirect(url_for('admin.plans'))

# =========================================
# --- Auditing and Accounting Routes ---
# =========================================

@admin_bp.route('/logs')
@login_required
@permission_required('view_logs')
def logs():
    """Displays the audit log of admin activities."""
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('admin_logs.html', logs=logs)

@admin_bp.route('/accounting')
@login_required
@permission_required('view_ledger')
def accounting():
    """Displays a ledger of all transactions in the system."""
    return render_template('admin_accounting.html', transactions=Transaction.query.order_by(Transaction.timestamp.desc()).limit(200).all())

@admin_bp.route('/test/distribute-profit', methods=['POST'])
@login_required
@permission_required('manage_settings')
def distribute_test_profit():
    """A test route to manually trigger the profit distribution background task."""
    count = run_profit_distribution(current_app._get_current_object())
    log_admin_activity('Distribute Profit', f'Manual run: {count} payouts')
    flash(f'Manual profit distribution completed. {count} payouts.', 'success')
    return redirect(url_for('admin.accounting'))