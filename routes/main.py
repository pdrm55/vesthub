from flask import Blueprint, render_template, request, session, flash, redirect, url_for, current_app
from models import InvestmentPlan
from utils import send_system_email

# تعریف Blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    if request.args.get('ref'): 
        session['ref_code'] = request.args.get('ref')
    
    plans = InvestmentPlan.query.filter_by(is_active=True).order_by(InvestmentPlan.duration_months.desc()).limit(3).all()
    return render_template('index.html', plans=plans)

@main_bp.route('/about')
def about():
    return render_template('about.html')

@main_bp.route('/plans')
def plans():
    plans = InvestmentPlan.query.filter_by(is_active=True).order_by(InvestmentPlan.duration_months.desc()).all()
    return render_template('plans.html', plans=plans)

@main_bp.route('/marketplace')
def marketplace():
    return render_template('marketplace.html')

@main_bp.route('/invest')
def invest_learn():
    return render_template('learn.html')

# --- Contact Us Routes ---

@main_bp.route('/contact-us')
def contact_us():
    """نمایش صفحه تماس با ما"""
    return render_template('contact.html')

@main_bp.route('/contact', methods=['POST'])
def contact():
    """پردازش فرم تماس با ما"""
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    message = request.form.get('message')
    
    email_body = f"""
    New Contact Message Received:
    
    Name: {name}
    Email: {email}
    Phone: {phone}
    
    Message:
    {message}
    """
    
    admin_email = current_app.config['MAIL_DEFAULT_SENDER'][1] if isinstance(current_app.config['MAIL_DEFAULT_SENDER'], tuple) else current_app.config['MAIL_DEFAULT_SENDER']
    
    send_system_email(f"New Contact from {name}", admin_email, email_body)
    
    flash('Thank you! Your message has been sent successfully.', 'success')
    return redirect(url_for('main.contact_us'))

# --- Legal Pages ---

@main_bp.route('/terms')
def terms():
    return render_template('terms.html')

@main_bp.route('/privacy')
def privacy():
    return render_template('privacy.html')

@main_bp.route('/risk-disclosure')
def risk_disclosure():
    return render_template('risk_disclosure.html')