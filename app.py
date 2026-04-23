import os
from flask import Flask, session, redirect, url_for, request
from dotenv import load_dotenv
from config import Config

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['TEMPLATES_AUTO_RELOAD'] = True

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    if not os.environ.get('VERCEL'):
        os.makedirs(os.path.join(app.root_path, 'demo'), exist_ok=True)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.upload import upload_bp
    from routes.report import report_bp
    from routes.suggestions import suggestions_bp
    from routes.chat import chat_bp
    from routes.timeline import timeline_bp
    from routes.model import model_bp
    from routes.export import export_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(suggestions_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(timeline_bp)
    app.register_blueprint(model_bp)
    app.register_blueprint(export_bp)

    # Protect all routes — redirect to login if not authenticated
    @app.before_request
    def require_login():
        allowed_endpoints = {
            'auth.login',
            'auth.guest_login',
            'auth.logout',
            'static',
            'model.csv_columns'
        }
        if request.endpoint in allowed_endpoints:
            return None
        if not session.get('authenticated'):
            return redirect(url_for('auth.login'))

    return app


# ✅ IMPORTANT: expose app for Vercel
app = create_app()


# Optional: local run
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=app.config.get('DEBUG', True))