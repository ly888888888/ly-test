from flask import Blueprint, request, jsonify
from models import db, TestCase, ApiDefinition, Project
from api.auth import require_permissions

testcases_bp = Blueprint('testcases', __name__)

@testcases_bp.route('', methods=['GET'])
@require_permissions('testcase:read', allow_anonymous=True)
def list_testcases():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    name = request.args.get('name')
    project_name = request.args.get('project')
    api_id = request.args.get('api_id')
    test_type = request.args.get('test_type')

    query = TestCase.query.join(Project, TestCase.project_id == Project.id).filter(TestCase.enabled == True)
    if name:
        query = query.filter(TestCase.name.like(f'%{name}%'))
    if project_name:
        query = query.filter(Project.name == project_name)
    if api_id:
        query = query.filter_by(api_id=api_id)
    if test_type:
        query = query.filter_by(test_type=test_type)

    paginated = query.paginate(page=page, per_page=page_size, error_out=False)
    cases = paginated.items

    return jsonify({
        'items': [{
            'id': c.id,
            'project': c.project,          # 通过 property 获取
            'project_id': c.project_id,
            'name': c.name,
            'api_id': c.api_id,
            'test_type': c.test_type,
            'params': c.params,
            'assertions': c.assertions,
            'extract': c.extract,
            'enabled': c.enabled,
            'created_at': c.created_at.isoformat() if c.created_at else None,
            'updated_at': c.updated_at.isoformat() if c.updated_at else None
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

    # 根据项目名称查找项目
    project = Project.query.filter_by(name=data['project']).first()
    if not project:
        return jsonify({'error': f'项目 "{data["project"]}" 不存在'}), 400
    if not project.enabled:
        return jsonify({'error': f'项目 "{data["project"]}" 已被禁用'}), 400

    api = ApiDefinition.query.get(data['api_id'])
    if not api:
        return jsonify({'error': 'api_id not found'}), 404

    case = TestCase(
        project_id=project.id,
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
    case = TestCase.query.filter_by(id=id, enabled=True).first_or_404()
    return jsonify({
        'id': case.id,
        'project': case.project,
        'project_id': case.project_id,
        'name': case.name,
        'description': case.description,
        'api_id': case.api_id,
        'test_type': case.test_type,
        'params': case.params,
        'assertions': case.assertions,
        'extract': case.extract,
        'expected_status': case.expected_status,
        'enabled': case.enabled,
        'created_at': case.created_at.isoformat() if case.created_at else None,
        'updated_at': case.updated_at.isoformat() if case.updated_at else None
    })

@testcases_bp.route('/<int:id>', methods=['PUT'])
@require_permissions('testcase:write')
def update_testcase(id):
    case = TestCase.query.get_or_404(id)
    data = request.get_json()
    if 'project' in data:
        project = Project.query.filter_by(name=data['project']).first()
        if not project:
            return jsonify({'error': f'项目 "{data["project"]}" 不存在'}), 400
        if not project.enabled:
            return jsonify({'error': f'项目 "{data["project"]}" 已被禁用'}), 400
        case.project_id = project.id
    for field in ['name', 'description', 'api_id', 'test_type', 'params', 'assertions', 'extract', 'expected_status', 'enabled']:
        if field in data:
            setattr(case, field, data[field])
    db.session.commit()
    return jsonify({'message': 'updated'})

@testcases_bp.route('/<int:id>', methods=['DELETE'])
@require_permissions('testcase:write')
def delete_testcase(id):
    case = TestCase.query.get_or_404(id)
    case.enabled = False
    db.session.commit()
    return jsonify({'message': 'deleted (soft)'})