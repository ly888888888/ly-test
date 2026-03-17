from flask import Blueprint, request, jsonify
from models import db, ApiDefinition
from api.auth import require_permissions

interfaces_bp = Blueprint('interfaces', __name__)

@interfaces_bp.route('', methods=['GET'])
@require_permissions('interface:read', allow_anonymous=True)
def list_interfaces():
    project = request.args.get('project')
    path = request.args.get('path')
    method = request.args.get('method')
    query = ApiDefinition.query
    if project:
        query = query.filter_by(project=project)
    if path:
        query = query.filter_by(path=path)
    if method:
        query = query.filter_by(method=method)
    interfaces = query.all()
    return jsonify([{
        'id': i.id,
        'project': i.project,
        'path': i.path,
        'method': i.method,
        'schema': i.schema,
        'description': i.description
    } for i in interfaces])

@interfaces_bp.route('', methods=['POST'])
@require_permissions('interface:write')
def create_interface():
    data = request.get_json()
    required = ['project', 'path', 'method', 'schema']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing fields'}), 400
    interface = ApiDefinition(
        project=data['project'],
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
    for field in ['project', 'path', 'method', 'schema', 'description']:
        if field in data:
            setattr(interface, field, data[field])
    db.session.commit()
    return jsonify({'message': 'updated'})

@interfaces_bp.route('/<int:id>', methods=['DELETE'])
@require_permissions('interface:write')
def delete_interface(id):
    interface = ApiDefinition.query.get_or_404(id)
    # 检查是否被用例引用，若有则拒绝删除
    if interface.test_cases:
        return jsonify({'error': 'Interface has test cases, cannot delete'}), 400
    db.session.delete(interface)
    db.session.commit()
    return jsonify({'message': 'deleted'})
