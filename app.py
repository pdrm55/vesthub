import os
import atexit
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, session
from flask_wtf.csrf import CSRFError
from werkzeug.middleware.proxy_fix import ProxyFix

from config import config
# FIX: Added 'babel' to imports
from extensions import db, login_manager, mail, scheduler, csrf, babel
from tasks import run_profit_distribution
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
    
    # --- Babel Configuration ---
    def get_locale():
        # 1. Check URL parameter
        lang = request.args.get('lang')
        if lang in app.config['LANGUAGES']:
            session['lang'] = lang
            return lang
        
        # 2. Check Session
        if session.get('lang'):
            return session.get('lang')
            
        # 3. Check Browser Headers
        return request.accept_languages.best_match(app.config['LANGUAGES'])

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
        return dict(has_permission=has_permission, get_locale=get_locale)

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
        return render_template('base.html', content=f"<h3>Security Error (400)</h3><p>{e.description}</p>"), 400

    @app.errorhandler(500)
    def internal_server_error(e):
        app.logger.error(f'Server Error: {e}')
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

    # Scheduler
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        if not scheduler.running:
            scheduler.add_job(
                func=lambda: run_profit_distribution(app), 
                trigger="cron", hour=0, minute=0, id='profit_distribution_job', replace_existing=True
            )
            try:
                scheduler.start()
                atexit.register(lambda: scheduler.shutdown())
            except:
                pass

    return app

# Create App instance for Gunicorn
app = create_app('production')
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)