from flask import Flask
from config import Config
from models import db
from api.interfaces import interfaces_bp
from api.testcases import testcases_bp
from api.run import run_bp
from api.functions import functions_bp
from api.flows import flows_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    # 注册蓝图
    app.register_blueprint(interfaces_bp, url_prefix='/api/interfaces')
    app.register_blueprint(testcases_bp, url_prefix='/api/testcases')
    app.register_blueprint(run_bp, url_prefix='/api/run')
    app.register_blueprint(functions_bp, url_prefix='/api/functions')
    app.register_blueprint(flows_bp, url_prefix='/api/flows')

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()  # 仅首次创建表
    app.run(debug=True, host='0.0.0.0', port=5000)
