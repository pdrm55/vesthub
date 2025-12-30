import os
import logging
import requests
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, session
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

        # 4. Check Browser Headers (Priority 4 - Fallback)
        # This handles cases like VPN users or standard browser preferences
        best_match = request.accept_languages.best_match(app.config['LANGUAGES'].keys())
        if best_match:
            session['lang'] = best_match
            return best_match
            
        # 5. Default
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


    return app

# Create App instance for Gunicorn
app = create_app('development')
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)