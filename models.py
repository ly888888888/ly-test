from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class ApiDefinition(db.Model):
    __tablename__ = 'api_definition'
    id = db.Column(db.Integer, primary_key=True)
    project = db.Column(db.String(50), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    method = db.Column(db.String(10), default='GET')
    schema = db.Column(db.JSON)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    test_cases = db.relationship('TestCase', backref='api', lazy=True)

class ParamTemplate(db.Model):
    __tablename__ = 'param_template'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.Enum('fixed','db_query','random'), nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TestCase(db.Model):
    __tablename__ = 'test_case'
    id = db.Column(db.Integer, primary_key=True)
    project = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    api_id = db.Column(db.Integer, db.ForeignKey('api_definition.id'), nullable=False)
    test_type = db.Column(db.Enum('smoke','structural','logic','compare','monitor','other'), nullable=False)
    params = db.Column(db.JSON, nullable=False)
    assertions = db.Column(db.JSON, nullable=True)  # 断言定义，可为空
    expected_status = db.Column(db.Integer, default=200)
    enabled = db.Column(db.Boolean, default=True)
    extract = db.Column(db.JSON, nullable=True)  # 新增
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    results = db.relationship('TestResult', backref='case', lazy=True)

class TestResult(db.Model):
    __tablename__ = 'test_result'
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('test_case.id'), nullable=False)
    run_id = db.Column(db.String(64), nullable=False)
    status = db.Column(db.Enum('success','fail','error'), nullable=False)
    http_status = db.Column(db.Integer)
    response_body = db.Column(db.Text)
    error_info = db.Column(db.Text)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    duration_ms = db.Column(db.Integer)

class TestFlow(db.Model):
    __tablename__ = 'test_flow'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    steps = db.Column(db.JSON, nullable=False)  # 步骤列表，每个步骤包含 api_id, params, extract, assertions 等
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)