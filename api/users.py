from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from models import db, User, UserPermission
from api.auth import require_permissions

users_bp = Blueprint('users', __name__)


def _set_permissions(user_id, perms):
    UserPermission.query.filter_by(user_id=user_id).delete()
    for p in perms or []:
        db.session.add(UserPermission(user_id=user_id, permission=p))


@users_bp.route('/users', methods=['GET'])
@require_permissions('admin')
def list_users():
    users = User.query.all()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'is_active': u.is_active,
        'created_at': u.created_at.isoformat() if u.created_at else None,
        'last_login_at': u.last_login_at.isoformat() if u.last_login_at else None,
        'permissions': [p.permission for p in u.permissions]
    } for u in users])


@users_bp.route('/users', methods=['POST'])
@require_permissions('admin')
def create_user():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'username/password required'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'username exists'}), 409
    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        is_active=data.get('is_active', True)
    )
    db.session.add(user)
    db.session.flush()
    _set_permissions(user.id, data.get('permissions', []))
    db.session.commit()
    return jsonify({'id': user.id}), 201


@users_bp.route('/users/<int:user_id>', methods=['GET'])
@require_permissions('admin')
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None,
        'permissions': [p.permission for p in user.permissions]
    })


@users_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_permissions('admin')
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    if 'password' in data and data['password']:
        user.password_hash = generate_password_hash(data['password'])
    if 'is_active' in data:
        user.is_active = bool(data['is_active'])
    if 'permissions' in data:
        _set_permissions(user.id, data.get('permissions', []))
    db.session.commit()
    return jsonify({'message': 'updated'})


@users_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_permissions('admin')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'deleted'})
