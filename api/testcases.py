from flask import Blueprint, request, jsonify
from models import db, TestCase, ApiDefinition
from api.auth import require_permissions

testcases_bp = Blueprint('testcases', __name__)

@testcases_bp.route('', methods=['GET'])
@require_permissions('testcase:read', allow_anonymous=True)
def list_testcases():
    # 分页参数
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    # 过滤参数
    name = request.args.get('name')
    project = request.args.get('project')
    api_id = request.args.get('api_id')
    test_type = request.args.get('test_type')

    query = TestCase.query.filter_by(enabled=True)
    if name:
        query = query.filter(TestCase.name.like(f'%{name}%'))
    if project:
        query = query.filter_by(project=project)
    if api_id:
        query = query.filter_by(api_id=api_id)
    if test_type:
        query = query.filter_by(test_type=test_type)

    paginated = query.paginate(page=page, per_page=page_size, error_out=False)
    cases = paginated.items

    return jsonify({
        'items': [{
            'id': c.id,
            'project': c.project,
            'name': c.name,
            'api_id': c.api_id,
            'test_type': c.test_type,
            'params': c.params,
            'assertions': c.assertions,
            'extract': c.extract,
            'enabled': c.enabled
        } for c in cases],
        'total': paginated.total,
        'page': page,
        'page_size': page_size
    })
@testcases_bp.route('', methods=['POST'])
@require_permissions('testcase:write')
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
        extract=data.get('extract'),
        expected_status=data.get('expected_status', 200),
        enabled=data.get('enabled', True)
    )
    db.session.add(case)
    db.session.commit()
    return jsonify({'id': case.id}), 201

@testcases_bp.route('/<int:id>', methods=['GET'])
@require_permissions('testcase:read', allow_anonymous=True)
def get_testcase(id):
    # 只返回启用的用例
    case = TestCase.query.filter_by(id=id, enabled=True).first_or_404()
    return jsonify({
        'id': case.id,
        'project': case.project,
        'name': case.name,
        'description': case.description,
        'api_id': case.api_id,
        'test_type': case.test_type,
        'params': case.params,
        'assertions': case.assertions,
        'extract': case.extract,
        'expected_status': case.expected_status,
        'enabled': case.enabled
    })

@testcases_bp.route('/<int:id>', methods=['PUT'])
@require_permissions('testcase:write')
def update_testcase(id):
    case = TestCase.query.get_or_404(id)
    data = request.get_json()
    for field in ['project', 'name', 'description', 'api_id', 'test_type', 'params', 'assertions', 'extract', 'expected_status', 'enabled']:
        if field in data:
            setattr(case, field, data[field])
    db.session.commit()
    return jsonify({'message': 'updated'})

@testcases_bp.route('/<int:id>', methods=['DELETE'])
@require_permissions('testcase:write')
def delete_testcase(id):
    # 软删除：将 enabled 设为 False
    case = TestCase.query.get_or_404(id)
    case.enabled = False
    db.session.commit()
    return jsonify({'message': 'deleted (soft)'})