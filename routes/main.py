from flask import Blueprint, render_template, request, session
from models import InvestmentPlan

# تعریف Blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    # ذخیره کد معرف در سشن اگر در لینک باشد
    if request.args.get('ref'): 
        session['ref_code'] = request.args.get('ref')
    
    # نمایش ۳ پلن برتر در صفحه اصلی
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

# --- اضافه شدن روت‌های حقوقی ---

@main_bp.route('/terms')
def terms():
    return render_template('terms.html')

@main_bp.route('/privacy')
def privacy():
    return render_template('privacy.html')

@main_bp.route('/risk-disclosure')
def risk_disclosure():
    return render_template('risk_disclosure.html')