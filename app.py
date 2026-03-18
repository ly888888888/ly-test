from flask import Flask
from config import Config
from models import db, ensure_default_admin
from api.interfaces import interfaces_bp
from api.testcases import testcases_bp
from api.run import run_bp
from api.functions import functions_bp
from api.flows import flows_bp
from api.auth import auth_bp
from api.users import users_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    # register blueprints
    app.register_blueprint(interfaces_bp, url_prefix='/api/interfaces')
    app.register_blueprint(testcases_bp, url_prefix='/api/testcases')
    app.register_blueprint(run_bp, url_prefix='/api/run')
    app.register_blueprint(functions_bp, url_prefix='/api/functions')
    app.register_blueprint(flows_bp, url_prefix='/api/flows')
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(users_bp, url_prefix='/api')

    @app.before_request
    def _init_default_admin_once():
        if app.config.get('_DEFAULT_ADMIN_INITED'):
            return
        ensure_default_admin(
            app.config.get('ADMIN_USER', 'admin'),
            app.config.get('ADMIN_PASSWORD', 'admin123'),
            permissions=['superadmin']
        )
        app.config['_DEFAULT_ADMIN_INITED'] = True

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()  # create tables on first run
        ensure_default_admin(
            app.config.get('ADMIN_USER', 'admin'),
            app.config.get('ADMIN_PASSWORD', 'admin123'),
            permissions=['superadmin']
        )
    app.run(debug=True, host='0.0.0.0', port=5000)
