import uuid
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.security import check_password_hash
from models import db, User, UserToken, UserPermission

auth_bp = Blueprint('auth', __name__)


def _get_token():
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:].strip()
    return request.headers.get('X-Token') or request.args.get('token')


def _get_user_permissions(user_id):
    perms = UserPermission.query.filter_by(user_id=user_id).all()
    return {p.permission for p in perms}


def require_permissions(*perms, allow_anonymous=False):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_app.config.get('AUTH_ENABLED', True):
                return fn(*args, **kwargs)
            if allow_anonymous:
                return fn(*args, **kwargs)
            token = _get_token()
            if not token:
                return jsonify({'error': 'auth required'}), 401
            token_rec = UserToken.query.filter_by(token=token, revoked=False).first()
            if not token_rec or token_rec.expires_at < datetime.utcnow():
                return jsonify({'error': 'invalid or expired token'}), 401
            user = token_rec.user
            if not user or not user.is_active:
                return jsonify({'error': 'user disabled'}), 403
            user_perms = _get_user_permissions(user.id)
            if 'admin' in user_perms:
                g.current_user = user
                return fn(*args, **kwargs)
            if perms and not set(perms).issubset(user_perms):
                return jsonify({'error': 'permission denied', 'required': list(perms)}), 403
            g.current_user = user
            return fn(*args, **kwargs)
        return wrapper
    return decorator


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'username/password required'}), 400
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'invalid credentials'}), 401
    if not user.is_active:
        return jsonify({'error': 'user disabled'}), 403
    token = uuid.uuid4().hex
    expires_at = datetime.utcnow() + timedelta(hours=current_app.config.get('TOKEN_EXPIRES_HOURS', 24))
    token_rec = UserToken(user_id=user.id, token=token, expires_at=expires_at)
    user.last_login_at = datetime.utcnow()
    db.session.add(token_rec)
    db.session.commit()
    perms = sorted(list(_get_user_permissions(user.id)))
    return jsonify({
        'token': token,
        'expires_at': expires_at.isoformat() + 'Z',
        'user_id': user.id,
        'permissions': perms
    })


@auth_bp.route('/logout', methods=['POST'])
@require_permissions()
def logout():
    token = _get_token()
    token_rec = UserToken.query.filter_by(token=token, revoked=False).first()
    if not token_rec:
        return jsonify({'error': 'invalid token'}), 400
    token_rec.revoked = True
    db.session.commit()
    return jsonify({'message': 'logged out'})
