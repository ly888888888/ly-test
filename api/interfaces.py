from flask import Blueprint, request, jsonify
from models import db, ApiDefinition, Project
from api.auth import require_permissions

interfaces_bp = Blueprint('interfaces', __name__)

@interfaces_bp.route('', methods=['GET'])
@require_permissions('interface:read', allow_anonymous=True)
def list_interfaces():
    # 分页参数
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    # 过滤参数
    project_name = request.args.get('project')
    path = request.args.get('path')
    method = request.args.get('method')

    query = ApiDefinition.query.join(Project, ApiDefinition.project_id == Project.id)
    if project_name:
        query = query.filter(Project.name == project_name)
    if path:
        query = query.filter(ApiDefinition.path == path)
    if method:
        query = query.filter(ApiDefinition.method == method)

    paginated = query.paginate(page=page, per_page=page_size, error_out=False)
    interfaces = paginated.items

    return jsonify({
        'items': [{
            'id': i.id,
            'project': i.project,
            'project_id': i.project_id,
            'path': i.path,
            'method': i.method,
            'schema': i.schema,
            'description': i.description
        } for i in interfaces],
        'total': paginated.total,
        'page': page,
        'page_size': page_size
    })

@interfaces_bp.route('', methods=['POST'])
@require_permissions('interface:write')
def create_interface():
    data = request.get_json()
    required = ['project', 'path', 'method', 'schema']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing fields'}), 400

    # 根据项目名称查找项目
    project = Project.query.filter_by(name=data['project']).first()
    if not project:
        return jsonify({'error': f'项目 "{data["project"]}" 不存在，请先创建项目'}), 400
    if not project.enabled:
        return jsonify({'error': f'项目 "{data["project"]}" 已被禁用，无法创建接口'}), 400

    # 检查重复
    existing = ApiDefinition.query.filter_by(
        project_id=project.id,
        path=data['path'],
        method=data['method']
    ).first()
    if existing:
        return jsonify({'error': '接口已存在（相同项目、路径和方法）'}), 400

    interface = ApiDefinition(
        project_id=project.id,
        path=data['path'],
        method=data['method'],
        schema=data['schema'],
        description=data.get('description')
    )
    db.session.add(interface)
    db.session.commit()
    return jsonify({'id': interface.id}), 201

@interfaces_bp.route('/<int:id>', methods=['GET'])
@require_permissions('interface:read', allow_anonymous=True)
def get_interface(id):
    interface = ApiDefinition.query.get_or_404(id)
    return jsonify({
        'id': interface.id,
        'project': interface.project,
        'project_id': interface.project_id,
        'path': interface.path,
        'method': interface.method,
        'schema': interface.schema,
        'description': interface.description
    })

@interfaces_bp.route('/<int:id>', methods=['PUT'])
@require_permissions('interface:write')
def update_interface(id):
    interface = ApiDefinition.query.get_or_404(id)
    data = request.get_json()
    # 如果传递了 project 字段，需要更新项目关联
    if 'project' in data:
        project = Project.query.filter_by(name=data['project']).first()
        if not project:
            return jsonify({'error': f'项目 "{data["project"]}" 不存在'}), 400
        if not project.enabled:
            return jsonify({'error': f'项目 "{data["project"]}" 已被禁用'}), 400
        interface.project_id = project.id
    for field in ['path', 'method', 'schema', 'description']:
        if field in data:
            setattr(interface, field, data[field])
    db.session.commit()
    return jsonify({'message': 'updated'})

@interfaces_bp.route('/<int:id>', methods=['DELETE'])
@require_permissions('interface:write')
def delete_interface(id):
    interface = ApiDefinition.query.get_or_404(id)
    if interface.test_cases:
        return jsonify({'error': 'Interface has test cases, cannot delete'}), 400
    db.session.delete(interface)
    db.session.commit()
    return jsonify({'message': 'deleted'})