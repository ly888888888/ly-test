from flask import Blueprint, request, jsonify
from models import db, TestCase, ApiDefinition

testcases_bp = Blueprint('testcases', __name__)

@testcases_bp.route('', methods=['GET'])
def list_testcases():
    project = request.args.get('project')
    api_id = request.args.get('api_id')
    test_type = request.args.get('test_type')
    query = TestCase.query
    if project:
        query = query.filter_by(project=project)
    if api_id:
        query = query.filter_by(api_id=api_id)
    if test_type:
        query = query.filter_by(test_type=test_type)
    cases = query.all()
    return jsonify([{
        'id': c.id,
        'project': c.project,
        'name': c.name,
        'api_id': c.api_id,
        'test_type': c.test_type,
        'params': c.params,
        'assertions': c.assertions,
        'enabled': c.enabled
    } for c in cases])

@testcases_bp.route('', methods=['POST'])
def create_testcase():
    data = request.get_json()
    required = ['project', 'name', 'api_id', 'test_type', 'params']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing fields'}), 400
    # 验证 api_id 存在
    api = ApiDefinition.query.get(data['api_id'])
    if not api:
        return jsonify({'error': 'api_id not found'}), 404
    case = TestCase(
        project=data['project'],
        name=data['name'],
        description=data.get('description'),
        api_id=data['api_id'],
        test_type=data['test_type'],
        params=data['params'],
        assertions=data.get('assertions'),
        expected_status=data.get('expected_status', 200),
        enabled=data.get('enabled', True)
    )
    db.session.add(case)
    db.session.commit()
    return jsonify({'id': case.id}), 201

@testcases_bp.route('/<int:id>', methods=['GET'])
def get_testcase(id):
    case = TestCase.query.get_or_404(id)
    return jsonify({
        'id': case.id,
        'project': case.project,
        'name': case.name,
        'description': case.description,
        'api_id': case.api_id,
        'test_type': case.test_type,
        'params': case.params,
        'assertions': case.assertions,
        'expected_status': case.expected_status,
        'enabled': case.enabled
    })

@testcases_bp.route('/<int:id>', methods=['PUT'])
def update_testcase(id):
    case = TestCase.query.get_or_404(id)
    data = request.get_json()
    for field in ['project', 'name', 'description', 'api_id', 'test_type', 'params', 'assertions', 'expected_status', 'enabled']:
        if field in data:
            setattr(case, field, data[field])
    db.session.commit()
    return jsonify({'message': 'updated'})

@testcases_bp.route('/<int:id>', methods=['DELETE'])
def delete_testcase(id):
    case = TestCase.query.get_or_404(id)
    db.session.delete(case)
    db.session.commit()
    return jsonify({'message': 'deleted'})