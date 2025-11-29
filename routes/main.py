from flask import Blueprint, render_template, request, session
from models import InvestmentPlan

# Define the Blueprint for the main, public-facing routes of the application.
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    """
    Home page route.
    - If a referral code is present in the URL ('?ref=...'), it's stored in the session.
    - Fetches the top 3 active investment plans to display on the homepage.
    """
    if request.args.get('ref'): 
        session['ref_code'] = request.args.get('ref')
    
    plans = InvestmentPlan.query.filter_by(is_active=True).order_by(InvestmentPlan.duration_months.desc()).limit(3).all()
    return render_template('index.html', plans=plans)

@main_bp.route('/about')
def about():
    """Renders the 'About Us' page."""
    return render_template('about.html')

@main_bp.route('/plans')
def plans():
    """Renders the 'Investment Plans' page, showing all active plans."""
    plans = InvestmentPlan.query.filter_by(is_active=True).order_by(InvestmentPlan.duration_months.desc()).all()
    return render_template('plans.html', plans=plans)

@main_bp.route('/marketplace')
def marketplace():
    """Renders the 'Marketplace' page for trading bots and tools."""
    return render_template('marketplace.html')

@main_bp.route('/invest')
def invest_learn():
    """Renders the 'Learn to Invest' educational page."""
    return render_template('learn.html')

# --- Legal & Compliance Routes ---

@main_bp.route('/terms')
def terms():
    """Renders the 'Terms & Conditions' page."""
    return render_template('terms.html')

@main_bp.route('/privacy')
def privacy():
    """Renders the 'Privacy Policy' page."""
    return render_template('privacy.html')

@main_bp.route('/risk-disclosure')
def risk_disclosure():
    """Renders the 'Risk Disclosure' page."""
    return render_template('risk_disclosure.html')