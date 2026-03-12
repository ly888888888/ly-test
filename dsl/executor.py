import ast
import json
import time
import uuid
from datetime import datetime

from dsl.context import Context
from dsl.extractor import Extractor
from dsl.assertion import AssertionEngine
from models import ApiDefinition, TestFlow, TestCase, FlowRun, FlowStepResult, db
from tools.http_client import HttpClient, RAWJSON
from api.utils import resolve_params, resolve_variables


def _safe_eval(expr):
    node = ast.parse(expr, mode="eval")
    for sub in ast.walk(node):
        if not isinstance(
            sub,
            (
                ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp,
                ast.Compare, ast.Name, ast.Load, ast.Constant,
                ast.And, ast.Or, ast.Not, ast.Eq, ast.NotEq,
                ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Add,
                ast.Sub, ast.Mult, ast.Div, ast.Mod,
            ),
        ):
            raise ValueError("Unsafe expression")
    return eval(compile(node, "<expr>", "eval"), {"__builtins__": {}})


def _eval_condition(cond, context):
    resolved = context.resolve(cond) if isinstance(cond, str) else cond
    if isinstance(resolved, str):
        return bool(_safe_eval(resolved))
    return bool(resolved)


def _resolve_step_from_case(step):
    case = TestCase.query.get(step.get('case_id'))
    if not case or not case.enabled:
        return None, {'step': step.get('name', ''), 'error': 'Case not found or disabled'}
    merged = {
        'name': step.get('name') or case.name,
        'api_id': case.api_id,
        'case_id': case.id,
        'params': case.params,
        'assertions': case.assertions,
        'extract': case.extract,
        'expected_status': case.expected_status,
    }
    for k in ['params', 'assertions', 'extract', 'expected_status', 'name']:
        if k in step:
            merged[k] = step[k]
    return merged, None


def _execute_http_step(step, host, context):
    step_start = time.time()
    if 'case_id' in step:
        step, err = _resolve_step_from_case(step)
        if err:
            return {
                'step': err.get('step', ''),
                'step_type': 'step',
                'status': 'error',
                'error_info': err.get('error'),
                'http_status': None,
                'response_body': None,
                'extracted': {},
                'api_id': None,
                'case_id': step.get('case_id'),
                'start_time': datetime.fromtimestamp(step_start),
                'end_time': datetime.fromtimestamp(step_start),
                'duration_ms': 0,
            }

    api = ApiDefinition.query.get(step['api_id'])
    if not api:
        step_end = time.time()
        return {
            'step': step.get('name', ''),
            'step_type': 'step',
            'status': 'error',
            'error_info': 'API not found',
            'http_status': None,
            'response_body': None,
            'extracted': {},
            'api_id': step.get('api_id'),
            'case_id': step.get('case_id'),
            'start_time': datetime.fromtimestamp(step_start),
            'end_time': datetime.fromtimestamp(step_end),
            'duration_ms': int((step_end - step_start) * 1000),
        }

    method = api.method.upper()
    raw_params = resolve_params(step.get('params', {}))
    final_params = resolve_variables(raw_params, context)

    if method == 'GET':
        query_str = HttpClient.querydict_to_querystr(final_params)
        url = HttpClient.makeHttpUrl(host, api.path, query_str)
        body = None
    else:
        query_str = ''
        url = HttpClient.makeHttpUrl(host, api.path, query_str)
        body = final_params

    try:
        if method == 'GET':
            res = HttpClient.http_get(url, bPrint=False)
        elif method == 'POST':
            res = HttpClient.http_post(url, bPrint=False, body=body, body_type=RAWJSON)
        elif method == 'PUT':
            res = HttpClient.http_put(url, bPrint=False, body=body, body_type=RAWJSON)
        elif method == 'DELETE':
            res = HttpClient.http_delete(url, bPrint=False, body=body, body_type=RAWJSON)
        else:
            raise ValueError(f"Unsupported method: {method}")
    except Exception as e:
        step_end = time.time()
        return {
            'step': step.get('name', ''),
            'step_type': 'step',
            'status': 'error',
            'error_info': f'Request failed: {str(e)}',
            'http_status': None,
            'response_body': None,
            'extracted': {},
            'api_id': step.get('api_id'),
            'case_id': step.get('case_id'),
            'start_time': datetime.fromtimestamp(step_start),
            'end_time': datetime.fromtimestamp(step_end),
            'duration_ms': int((step_end - step_start) * 1000),
        }

    response_json = json.loads(res.text) if res else {}
    http_status = res.status_code if res else 0

    step_success = True
    error_msgs = []
    expected_status = step.get('expected_status', 200)
    if http_status != expected_status:
        step_success = False
        error_msgs.append(f'HTTP status {http_status} != {expected_status}')
    for assertion in step.get('assertions', []):
        ok, msg = AssertionEngine.assert_one(assertion, response_json, context)
        if not ok:
            step_success = False
            error_msgs.append(msg)

    extracted = {}
    if step.get('extract'):
        extracted = Extractor.extract(response_json, step['extract'])
        if step.get('name'):
            context.set_by_path(f"steps.{step['name']}", extracted)

    step_end = time.time()
    return {
        'step': step.get('name', ''),
        'step_type': 'step',
        'status': 'success' if step_success else 'fail',
        'http_status': http_status,
        'error_info': "; ".join(error_msgs) if error_msgs else None,
        'response_body': res.text if res else None,
        'extracted': extracted,
        'api_id': step.get('api_id'),
        'case_id': step.get('case_id'),
        'start_time': datetime.fromtimestamp(step_start),
        'end_time': datetime.fromtimestamp(step_end),
        'duration_ms': int((step_end - step_start) * 1000),
    }


def _execute_steps(steps, host, context, depth, max_depth, iteration_index):
    if depth > max_depth:
        return [{
            'step': '',
            'step_type': 'control',
            'status': 'error',
            'error_info': 'Max depth exceeded',
            'http_status': None,
            'response_body': None,
            'extracted': {},
            'api_id': None,
            'case_id': None,
            'start_time': datetime.utcnow(),
            'end_time': datetime.utcnow(),
            'duration_ms': 0,
            'iteration_index': iteration_index,
            'step_index': None,
        }]
    results = []
    for idx, step in enumerate(steps):
        step_type = step.get('type', 'step')
        if step_type == 'step':
            r = _execute_http_step(step, host, context)
            r['iteration_index'] = iteration_index
            r['step_index'] = idx
            results.append(r)
        elif step_type == 'condition':
            cond = step.get('if')
            if cond is None:
                results.append({
                    'step': step.get('name', ''),
                    'step_type': 'condition',
                    'status': 'error',
                    'error_info': 'Missing condition',
                    'http_status': None,
                    'response_body': None,
                    'extracted': {},
                    'api_id': None,
                    'case_id': None,
                    'start_time': datetime.utcnow(),
                    'end_time': datetime.utcnow(),
                    'duration_ms': 0,
                    'iteration_index': iteration_index,
                    'step_index': idx,
                })
                continue
            cond_ok = _eval_condition(cond, context)
            results.append({
                'step': step.get('name', ''),
                'step_type': 'condition',
                'status': 'success',
                'error_info': None,
                'http_status': None,
                'response_body': None,
                'extracted': {},
                'api_id': None,
                'case_id': None,
                'start_time': datetime.utcnow(),
                'end_time': datetime.utcnow(),
                'duration_ms': 0,
                'iteration_index': iteration_index,
                'step_index': idx,
            })
            branch = step.get('then', []) if cond_ok else step.get('else', [])
            results.extend(_execute_steps(branch, host, context, depth + 1, max_depth, iteration_index))
        elif step_type == 'loop':
            times = step.get('times', 0)
            if isinstance(times, str):
                times = context.resolve(times)
            try:
                times = int(times)
            except Exception:
                results.append({
                    'step': step.get('name', ''),
                    'step_type': 'loop',
                    'status': 'error',
                    'error_info': 'Invalid loop times',
                    'http_status': None,
                    'response_body': None,
                    'extracted': {},
                    'api_id': None,
                    'case_id': None,
                    'start_time': datetime.utcnow(),
                    'end_time': datetime.utcnow(),
                    'duration_ms': 0,
                    'iteration_index': iteration_index,
                    'step_index': idx,
                })
                continue
            results.append({
                'step': step.get('name', ''),
                'step_type': 'loop',
                'status': 'success',
                'error_info': None,
                'http_status': None,
                'response_body': None,
                'extracted': {},
                'api_id': None,
                'case_id': None,
                'start_time': datetime.utcnow(),
                'end_time': datetime.utcnow(),
                'duration_ms': 0,
                'iteration_index': iteration_index,
                'step_index': idx,
            })
            for _ in range(times):
                results.extend(_execute_steps(step.get('steps', []), host, context, depth + 1, max_depth, iteration_index))
        else:
            results.append({
                'step': step.get('name', ''),
                'step_type': step_type,
                'status': 'error',
                'error_info': f'Unknown step type: {step_type}',
                'http_status': None,
                'response_body': None,
                'extracted': {},
                'api_id': None,
                'case_id': None,
                'start_time': datetime.utcnow(),
                'end_time': datetime.utcnow(),
                'duration_ms': 0,
                'iteration_index': iteration_index,
                'step_index': idx,
            })
    return results


def execute_flow(flow_id, host, host_compare=None):
    flow = TestFlow.query.get(flow_id)
    if not flow or not flow.enabled:
        return {'error': 'Flow not found or disabled'}

    run_id = str(uuid.uuid4())
    run_start = time.time()
    flow_run = FlowRun(
        flow_id=flow_id,
        run_id=run_id,
        status='running',
        start_time=datetime.fromtimestamp(run_start)
    )
    db.session.add(flow_run)
    db.session.commit()

    results = []
    max_depth = 10

    failed = False
    if flow.data_source:
        for idx, row in enumerate(flow.data_source):
            context = Context()
            context.set_by_path("data", row)
            step_results = _execute_steps(flow.steps, host, context, 0, max_depth, idx)
            results.append({'data': row, 'results': step_results})

            for r in step_results:
                if r.get('status') in ['fail', 'error']:
                    failed = True
                record = FlowStepResult(
                    flow_run_id=flow_run.id,
                    step_name=r.get('step'),
                    step_type=r.get('step_type'),
                    step_index=r.get('step_index'),
                    iteration_index=r.get('iteration_index'),
                    case_id=r.get('case_id'),
                    api_id=r.get('api_id'),
                    status=r.get('status'),
                    http_status=r.get('http_status'),
                    response_body=(r.get('response_body') or '')[:65535],
                    error_info=r.get('error_info'),
                    extracted=r.get('extracted'),
                    data_row=row,
                    start_time=r.get('start_time'),
                    end_time=r.get('end_time'),
                    duration_ms=r.get('duration_ms'),
                )
                db.session.add(record)
    else:
        context = Context()
        results = _execute_steps(flow.steps, host, context, 0, max_depth, 0)

        for r in results:
            if r.get('status') in ['fail', 'error']:
                failed = True
            record = FlowStepResult(
                flow_run_id=flow_run.id,
                step_name=r.get('step'),
                step_type=r.get('step_type'),
                step_index=r.get('step_index'),
                iteration_index=r.get('iteration_index'),
                case_id=r.get('case_id'),
                api_id=r.get('api_id'),
                status=r.get('status'),
                http_status=r.get('http_status'),
                response_body=(r.get('response_body') or '')[:65535],
                error_info=r.get('error_info'),
                extracted=r.get('extracted'),
                data_row=None,
                start_time=r.get('start_time'),
                end_time=r.get('end_time'),
                duration_ms=r.get('duration_ms'),
            )
            db.session.add(record)

    run_end = time.time()
    flow_run.status = 'fail' if failed else 'success'
    flow_run.end_time = datetime.fromtimestamp(run_end)
    flow_run.duration_ms = int((run_end - run_start) * 1000)
    db.session.commit()

    return {'flow_id': flow_id, 'run_id': run_id, 'results': results}
