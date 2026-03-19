import json
from flask import Blueprint, request, jsonify
from models import db, ParamTemplate
from api.auth import require_permissions
from tools.conf import TestDB
from api import custom_functions

param_templates_bp = Blueprint('param_templates', __name__)


def _validate_type(t):
    return t in ['fixed', 'db_query', 'random', 'function']


def _resolve_template(tmpl):
    if tmpl.type == 'fixed':
        try:
            return json.loads(tmpl.value)
        except Exception:
            return tmpl.value
    if tmpl.type == 'db_query':
        sql = tmpl.value
        conn = TestDB.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchone()
                return result[0] if result else None
        finally:
            conn.close()
    if tmpl.type == 'function':
        func_name = None
        args = {}
        try:
            payload = json.loads(tmpl.value)
            if isinstance(payload, dict):
                func_name = payload.get('function')
                args = payload.get('args', {})
        except Exception:
            func_name = tmpl.value
        if not func_name:
            raise ValueError('function name required')
        func = getattr(custom_functions, func_name, None)
        if func is None:
            raise ValueError(f'Function {func_name} not found')
        return func(**args)
    if tmpl.type == 'random':
        return tmpl.value if tmpl.value is not None else 'random_value'
    raise ValueError(f'Unknown template type: {tmpl.type}')


@param_templates_bp.route('', methods=['GET'])
@require_permissions('param:read')
def list_templates():
    templates = ParamTemplate.query.all()
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'type': t.type,
        'value': t.value,
        'description': t.description,
        'created_at': t.created_at.isoformat() if t.created_at else None
    } for t in templates])


@param_templates_bp.route('', methods=['POST'])
@require_permissions('param:write')
def create_template():
    data = request.get_json() or {}
    name = data.get('name')
    t = data.get('type')
    value = data.get('value')
    if not name or not t or value is None:
        return jsonify({'error': 'name/type/value required'}), 400
    if not _validate_type(t):
        return jsonify({'error': 'invalid type'}), 400
    tmpl = ParamTemplate(
        name=name,
        type=t,
        value=value,
        description=data.get('description')
    )
    db.session.add(tmpl)
    db.session.commit()
    return jsonify({'id': tmpl.id}), 201


@param_templates_bp.route('/<int:tmpl_id>', methods=['PUT'])
@require_permissions('param:write')
def update_template(tmpl_id):
    tmpl = ParamTemplate.query.get_or_404(tmpl_id)
    data = request.get_json() or {}
    if 'name' in data:
        tmpl.name = data['name']
    if 'type' in data:
        if not _validate_type(data['type']):
            return jsonify({'error': 'invalid type'}), 400
        tmpl.type = data['type']
    if 'value' in data:
        tmpl.value = data['value']
    if 'description' in data:
        tmpl.description = data['description']
    db.session.commit()
    return jsonify({'message': 'updated'})


@param_templates_bp.route('/<int:tmpl_id>', methods=['DELETE'])
@require_permissions('param:write')
def delete_template(tmpl_id):
    tmpl = ParamTemplate.query.get_or_404(tmpl_id)
    db.session.delete(tmpl)
    db.session.commit()
    return jsonify({'message': 'deleted'})


@param_templates_bp.route('/preview', methods=['POST'])
@require_permissions('param:read')
def preview_template():
    data = request.get_json() or {}
    tmpl = None
    tmpl_id = data.get('id')
    tmpl_name = data.get('name')
    if tmpl_id:
        tmpl = ParamTemplate.query.get(tmpl_id)
    elif tmpl_name:
        tmpl = ParamTemplate.query.filter_by(name=tmpl_name).first()
    else:
        # ad-hoc preview
        name = data.get('name', '_tmp')
        t = data.get('type')
        value = data.get('value')
        if not _validate_type(t):
            return jsonify({'error': 'invalid type'}), 400
        tmpl = ParamTemplate(name=name, type=t, value=value, description=data.get('description'))
    if tmpl is None:
        return jsonify({'error': 'template not found'}), 404
    try:
        resolved = _resolve_template(tmpl)
        return jsonify({'resolved': resolved})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
