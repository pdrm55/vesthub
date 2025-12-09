import os
import atexit
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template , request, session
from flask_wtf.csrf import CSRFError
# Add ProxyFix import
from werkzeug.middleware.proxy_fix import ProxyFix

from config import config
from extensions import db, login_manager, mail, scheduler, csrf , babel
from tasks import run_profit_distribution
from utils import has_permission

# Import Blueprints
from routes.auth import auth_bp
from routes.main import main_bp
from routes.user import user_bp
from routes.admin import admin_bp

def create_app(config_name='default'):
    app = Flask(__name__)
    
    app.config.from_object(config[config_name])
    
    # Init Extensions
    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Register Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    
    # --- تنظیمات زبان (Babel) ---
    def get_locale():
        # 1. اگر کاربر زبان را در URL فرستاد (مثلا ?lang=tr)
        lang = request.args.get('lang')
        if lang in app.config['LANGUAGES']:
            session['lang'] = lang
            return lang
        
        # 2. اگر قبلاً زبان را انتخاب کرده و در سشن هست
        if session.get('lang'):
            return session.get('lang')
            
        # 3. تشخیص هوشمند بر اساس مرورگر کاربر
        return request.accept_languages.best_match(app.config['LANGUAGES'])

    babel.init_app(app, locale_selector=get_locale)


    @app.context_processor
    def inject_utilities():
        return dict(has_permission=has_permission)

    from models import User
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # --- Error Handlers ---
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('base.html', content="<h3>404 - Page Not Found</h3><p>The page you are looking for does not exist.</p>"), 404

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return render_template('base.html', content=f"<h3>Security Error (400)</h3><p>{e.description}</p>"), 400

    @app.errorhandler(500)
    def internal_server_error(e):
        app.logger.error(f'Server Error: {e}')
        return render_template('base.html', content="<h3>Internal Server Error (500)</h3><p>We are experiencing technical difficulties. Please try again later.</p>"), 500

    # Logging Setup
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/vesthub.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('VestHub startup')

    # Scheduler Setup (Only runs if not using Gunicorn worker reloading, or manage externally)
    # Note: In production with multiple Gunicorn workers, usually the scheduler is run as a separate process.
    # For simplicity on a single server, we keep it here but ensure it runs only once if possible.
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
         if not scheduler.running:
            scheduler.add_job(
                func=lambda: run_profit_distribution(app), 
                trigger="cron", 
                hour=0, 
                minute=0,
                id='profit_distribution_job',
                replace_existing=True
            )
            try:
                scheduler.start()
                atexit.register(lambda: scheduler.shutdown())
            except:
                pass

    return app

# --- اصلاح نهایی برای HTTPS ---
# Create the app instance for Gunicorn
app = create_app('production')

# Add ProxyFix for HTTPS support
# This tells Flask to trust headers from Nginx (like X-Forwarded-Proto: https)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

if __name__ == '__main__':
    # This part runs only when executing `python app.py` directly for testing
    app.run(debug=True, host='0.0.0.0', port=5000)