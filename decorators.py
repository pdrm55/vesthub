from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user

def permission_required(permission_name):
    """
    Custom decorator to check user permissions before accessing a route.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. Check if user is authenticated
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            # 2. Super Admin always has access
            if current_user.role and current_user.role.name == 'Admin':
                return f(*args, **kwargs)

            # 3. Check specific permission
            if current_user.role and current_user.role.permissions:
                permissions = current_user.role.permissions.split(',')
                if permission_name in permissions:
                    return f(*args, **kwargs)
            
            # 4. Access Denied
            flash('You do not have the required permissions to perform this action.', 'danger')
            
            # Redirect logic
            if current_user.role and ('admin' in current_user.role.name.lower()):
                 return redirect(url_for('admin.dashboard'))
            return redirect(url_for('main.home'))
            
        return decorated_function
    return decorator

def admin_required(f):
    """Shortcut decorator for super admin access only"""
    return permission_required('manage_roles')(f)