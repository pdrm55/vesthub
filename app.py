import os
import logging
import requests
import click
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, session
from flask_mail import Message
from flask_wtf.csrf import CSRFError
from werkzeug.middleware.proxy_fix import ProxyFix

from config import config
# FIX: Added 'babel' to imports
from extensions import db, login_manager, mail, csrf, babel, oauth
from tasks import process_missed_profits
from utils import has_permission

from routes.auth import auth_bp
from routes.main import main_bp
from routes.user import user_bp
from routes.admin import admin_bp

def create_app(config_name='default'):
    app = Flask(__name__)
    
    # Load Config
    app.config.from_object(config[config_name])
    
    # Init Extensions
    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    oauth.init_app(app)
    
    # Register Google OAuth
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )
    
    # --- Babel Configuration ---
    def get_locale():
        # 1. Check URL parameter (Priority 1)
        lang = request.args.get('lang')
        if lang in app.config['LANGUAGES']:
            session['lang'] = lang
            return lang
        
        # 2. Check Session (Priority 2 - Persistence)
        if session.get('lang'):
            return session.get('lang')

        # 3. IP Geolocation Check (Priority 3 - For First Time Visitors)
        # We perform this check only if session is not set to avoid API latency on every request
        try:
            # Check Cloudflare Header first (Best for Production)
            country = request.headers.get('CF-IPCountry')
            
            # If not behind Cloudflare, try basic API (with short timeout)
            if not country:
                user_ip = request.remote_addr
                # Skip local development IPs
                if user_ip not in ['127.0.0.1', 'localhost']:
                    # Use a free lightweight API with 1s timeout to prevent hanging
                    response = requests.get('http://ip-api.com/json/{}?fields=countryCode'.format(user_ip), timeout=1)
                    if response.status_code == 200:
                        country = response.json().get('countryCode')

            # Logic for Specific Countries
            if country == 'IR':
                session['lang'] = 'fa'
                return 'fa'
            elif country == 'TR':
                session['lang'] = 'tr'
                return 'tr'
                
        except Exception:
            # If API fails or times out, silently fall back to browser
            pass

        # 4. Default — all other IPs get English
        return 'en'

    # Initialize Babel
    babel.init_app(app, locale_selector=get_locale)
    
    # Register Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    
    # Context Processors
    @app.context_processor
    def inject_utilities():
        # Inject get_locale to be used in templates (base.html)
        return dict(has_permission=has_permission, get_locale=get_locale, languages=app.config.get('LANGUAGES', {}))

    from models import User
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('base.html', content="<h3>404 - Page Not Found</h3>"), 404

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return render_template('base.html', content="<h3>Security Error (400)</h3><p>{}</p>".format(e.description)), 400

    @app.errorhandler(500)
    def internal_server_error(e):
        app.logger.error('Server Error: {}'.format(e))
        # Note: Ensure get_locale is available or base.html handles its absence
        return render_template('base.html', content="<h3>Internal Server Error (500)</h3><p>We are experiencing technical difficulties. Please try again later.</p>"), 500

    # Logging
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/vesthub.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('VestHub startup')

    # Register CLI Commands
    @app.cli.command('recover-profits')
    def recover_profits_command():
        """Manually trigger profit backfill and recovery."""
        process_missed_profits(app)
        
    # ... کدهای قبلی ...
    # ... کدهای قبلی ...

    # Register CLI Commands
    @app.cli.command('recover-profits')
    def recover_profits_command():
        """Manually trigger profit backfill and recovery."""
        print("Starting recovery process...")
        count = process_missed_profits(app)
        print(f"Recovery finished. Total transactions created: {count}")

    @app.cli.command('send-marketing-reminders')
    def send_marketing_reminders_command():
        """Send marketing emails to users who haven't invested after 3 days."""
        from models import User, Investment
        print("Starting marketing reminders process...")
        
        threshold_date = datetime.utcnow() - timedelta(days=3)
        users = User.query.filter(User.created_at <= threshold_date, User.marketing_email_sent == False).all()
        
        sent_count = 0
        for user in users:
            try:
                # Check if the user has any investments
                has_investment = Investment.query.filter_by(user_id=user.id).first()
                
                if not has_investment:
                    # Send the marketing email
                    msg = Message("Start Your Journey with VestHub", recipients=[user.email])
                    
                    rendered_html = render_template('emails/market_email.html', user=user)
                    if not rendered_html or not rendered_html.strip():
                        app.logger.warning(f"Template rendered empty for {user.email}. Check market_email.html on the server.")
                        
                    msg.html = rendered_html
                    msg.body = (
                        f"Hello {user.first_name},\n\n"
                        "It's been a few days since you joined VestHub, and we wanted to check in on you. "
                        "We noticed you haven't started your first investment yet.\n\n"
                        "Explore Investment Plans: https://vesthub.com/invest\n\n"
                        "Best regards,\nThe VestHub Team"
                    )
                    
                    mail.send(msg)
                    sent_count += 1
                    app.logger.info(f"Successfully sent marketing email to {user.email}")
                
                # چه ایمیل ارسال شده باشد و چه کاربر قبلاً سرمایه‌گذاری کرده باشد، 
                # وضعیت را True می‌کنیم تا در روزهای آینده دوباره بررسی نشود.
                user.marketing_email_sent = True
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Error processing marketing email for {user.email}: {str(e)}")
                
        print(f"Marketing reminders process completed. Sent {sent_count} emails.")

    @app.cli.command('test-email')
    @click.argument('target_email')
    def test_email_command(target_email):
        """Send a test marketing email to a specific address."""
        from models import User
        print(f"Preparing test email for: {target_email} ...")
        
        # سعی می‌کنیم کاربر را از دیتابیس پیدا کنیم تا نام او در قالب قرار گیرد
        user = User.query.filter_by(email=target_email).first()
        if not user:
            # اگر کاربر وجود نداشت، یک آبجکت موقت می‌سازیم تا خطای رندر ندهد
            class MockUser:
                first_name = "TestUser"
                email = target_email
            user = MockUser()
            print("User not found in database. Using mock data (Name: TestUser).")
            
        try:
            msg = Message("Test: Start Your Journey with VestHub", recipients=[target_email])
            msg.html = render_template('emails/market_email.html', user=user)
            msg.body = "This is a test email. Please view in an HTML-compatible client."
            mail.send(msg)
            print(f"✅ Test email successfully sent to {target_email}")
        except Exception as e:
            print(f"❌ Error sending test email: {str(e)}")

    return app

# Create App instance for Gunicorn
app = create_app('development')
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)