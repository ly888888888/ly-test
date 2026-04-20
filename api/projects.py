from flask import Blueprint, request, jsonify
from models import db, Project, TestCase, ApiDefinition  # 确保导入 TestCase
from api.auth import require_permissions

projects_bp = Blueprint('projects', __name__)

@projects_bp.route('', methods=['GET'])
@require_permissions('project:read')
def list_projects():
    """获取所有项目列表"""
    projects = Project.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'enabled': p.enabled,
        'created_at': p.created_at.isoformat() if p.created_at else None,
        'updated_at': p.updated_at.isoformat() if p.updated_at else None
    } for p in projects])

@projects_bp.route('', methods=['POST'])
@require_permissions('project:write')
def create_project():
    """创建新项目"""
    data = request.get_json() or {}
    name = data.get('name')
    if not name:
        return jsonify({'error': '项目名称不能为空'}), 400
    if Project.query.filter_by(name=name).first():
        return jsonify({'error': '项目名称已存在'}), 409
    project = Project(
        name=name,
        description=data.get('description', ''),
        enabled=data.get('enabled', True)
    )
    db.session.add(project)
    db.session.commit()
    return jsonify({'id': project.id}), 201

@projects_bp.route('/<int:project_id>', methods=['PUT'])
@require_permissions('project:write')
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.get_json() or {}
    if 'name' in data:
        new_name = data['name'].strip()
        if new_name != project.name:
            existing = Project.query.filter(Project.name == new_name, Project.id != project_id).first()
            if existing:
                return jsonify({'error': '项目名称已存在'}), 409
            project.name = new_name
    if 'description' in data:
        project.description = data['description']
    if 'enabled' in data:
        project.enabled = bool(data['enabled'])
    db.session.commit()
    return jsonify({'message': 'updated'})

@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@require_permissions('project:write')
def delete_project(project_id):
    """删除项目，前提是项目下没有接口和流程"""
    project = Project.query.get_or_404(project_id)
    if project.apis or project.flows:
        return jsonify({'error': '项目下存在接口或流程，无法删除'}), 400
    db.session.delete(project)
    db.session.commit()
    return jsonify({'message': 'deleted'})