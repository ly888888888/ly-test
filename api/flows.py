from flask import Blueprint, request, jsonify, current_app
from models import db, TestFlow, FlowRun, FlowStepResult
from dsl.executor import execute_flow
from dsl.parser import validate_flow_steps

flows_bp = Blueprint('flows', __name__)


@flows_bp.route('', methods=['GET'])
def list_flows():
    query = TestFlow.query
    flows = query.all()
    return jsonify([{
        'id': f.id,
        'name': f.name,
        'description': f.description,
        'steps': f.steps,
        'data_source': f.data_source,
        'enabled': f.enabled
    } for f in flows])


@flows_bp.route('/<int:flow_id>', methods=['GET'])
def get_flow(flow_id):
    flow = TestFlow.query.get_or_404(flow_id)
    return jsonify({
        'id': flow.id,
        'name': flow.name,
        'description': flow.description,
        'steps': flow.steps,
        'data_source': flow.data_source,
        'enabled': flow.enabled
    })


@flows_bp.route('', methods=['POST'])
def create_flow():
    data = request.get_json() or {}
    required = ['name', 'steps']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing fields'}), 400

    try:
        validate_flow_steps(data['steps'])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    flow = TestFlow(
        name=data['name'],
        description=data.get('description'),
        steps=data['steps'],
        data_source=data.get('data_source'),
        enabled=data.get('enabled', True)
    )
    db.session.add(flow)
    db.session.commit()
    return jsonify({'id': flow.id}), 201


@flows_bp.route('/<int:flow_id>', methods=['PUT'])
def update_flow(flow_id):
    flow = TestFlow.query.get_or_404(flow_id)
    data = request.get_json() or {}
    if 'steps' in data:
        try:
            validate_flow_steps(data['steps'])
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    for field in ['name', 'description', 'steps', 'data_source', 'enabled']:
        if field in data:
            setattr(flow, field, data[field])
    db.session.commit()
    return jsonify({'message': 'updated'})


@flows_bp.route('/<int:flow_id>', methods=['DELETE'])
def delete_flow(flow_id):
    flow = TestFlow.query.get_or_404(flow_id)
    db.session.delete(flow)
    db.session.commit()
    return jsonify({'message': 'deleted'})


@flows_bp.route('/<int:flow_id>/run', methods=['POST'])
def run_flow(flow_id):
    data = request.get_json() or {}
    host = data.get('host', current_app.config.get('DEFAULT_HOST', '172.17.12.101:9500'))
    host_compare = data.get('host_compare', None)
    result = execute_flow(flow_id, host, host_compare=host_compare)
    return jsonify(result)


@flows_bp.route('/results/<run_id>', methods=['GET'])
def get_flow_results(run_id):
    run = FlowRun.query.filter_by(run_id=run_id).first()
    if not run:
        return jsonify({'error': 'run_id not found'}), 404
    steps = FlowStepResult.query.filter_by(flow_run_id=run.id).all()
    return jsonify({
        'flow_id': run.flow_id,
        'run_id': run.run_id,
        'status': run.status,
        'start_time': run.start_time.isoformat() if run.start_time else None,
        'end_time': run.end_time.isoformat() if run.end_time else None,
        'duration_ms': run.duration_ms,
        'steps': [{
            'step_name': s.step_name,
            'step_type': s.step_type,
            'step_index': s.step_index,
            'iteration_index': s.iteration_index,
            'case_id': s.case_id,
            'api_id': s.api_id,
            'status': s.status,
            'http_status': s.http_status,
            'error_info': s.error_info,
            'extracted': s.extracted,
            'start_time': s.start_time.isoformat() if s.start_time else None,
            'duration_ms': s.duration_ms
        } for s in steps]
    })
