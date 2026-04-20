import json
import uuid
import time
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from models import db, TestCase, ApiDefinition, TestResult, FlowRun, FlowStepResult
from tools.http_client import HttpClient, RAWJSON
from tools.json_validate import struct_validate_get, struct_validate_post, struct_validate_put, struct_validate_delete
from tools.conf import TestLogInfo, TestAssert
from .utils import resolve_params, resolve_variables
from tools import compare_test_common
from dsl.context import Context
from dsl.extractor import Extractor
from dsl.assertion import AssertionEngine
from api.auth import require_permissions

run_bp = Blueprint('run', __name__)


def execute_case(case_id, host, run_id=None, host_compare=None):
    """
    执行单个测试用例，返回结果字典，并记录到数据库
    """
    if run_id is None:
        run_id = str(uuid.uuid4())
    case = TestCase.query.get(case_id)
    if not case or not case.enabled:
        return {'error': 'Case not found or disabled'}

    api = case.api
    method = api.method.upper()
    context = Context()
    # 解析参数
    try:
        params = resolve_params(case.params)
        params = resolve_variables(params, context)
    except Exception as e:
        # 参数解析失败记录为 error
        result = TestResult(
            case_id=case_id,
            run_id=run_id,
            status='error',
            error_info=f'Param resolve error: {str(e)}',
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_ms=0
        )
        db.session.add(result)
        db.session.commit()
        return {'case_id': case_id, 'status': 'error', 'error': str(e)}

    if method == 'GET':
        query_str = HttpClient.querydict_to_querystr(params)
        url = HttpClient.makeHttpUrl(host, api.path, query_str)
        body = None
        body_type = None
    else:
        query_str = ''
        url = HttpClient.makeHttpUrl(host, api.path, query_str)
        body = params
        body_type = RAWJSON  # 默认 JSON
    print(url)

    start = time.time()
    try:
        if case.test_type == 'smoke':
            # 发送请求
            if method == 'GET':
                res = HttpClient.http_get(url, bPrint=False)
            elif method == 'POST':
                res = HttpClient.http_post(url, bPrint=False, body=body, body_type=body_type)
            elif method == 'PUT':
                res = HttpClient.http_put(url, bPrint=False, body=body, body_type=body_type)
            elif method == 'DELETE':
                res = HttpClient.http_delete(url, bPrint=False, body=body, body_type=body_type)
            else:
                raise ValueError(f"Unsupported method: {method}")

            http_status = res.status_code if res else 0
            success = (res is not None and res.status_code == case.expected_status)
            error_info = '' if success else f'HTTP status {http_status} != {case.expected_status}'
            response_body = res.text if res else ''
        elif case.test_type == 'structural':
            # 使用 json_validate
            tli = TestLogInfo()
            tli.url = url
            tli.api_id = case.id
            tli.case_desc = case.name

            if method == 'GET':
                result = struct_validate_get(tli, api.schema)
            elif method == 'POST':
                result = struct_validate_post(tli, api.schema, post_body=body, body_type=body_type)
            elif method == 'PUT':
                result = struct_validate_put(tli, api.schema, put_body=body, body_type=body_type)
            elif method == 'DELETE':
                result = struct_validate_delete(tli, api.schema, delete_body=body, body_type=body_type)
            else:
                raise ValueError(f"Unsupported method for structural test: {method}")

            success = result.test_result == TestAssert.success
            http_status = result.http_status
            error_info = result.error_info
            response_body = ''
        elif case.test_type in ['logic', 'monitor']:
            # 发送请求（同 smoke 分支）
            if method == 'GET':
                res = HttpClient.http_get(url, bPrint=False)
            elif method == 'POST':
                res = HttpClient.http_post(url, bPrint=False, body=body, body_type=body_type)
            elif method == 'PUT':
                res = HttpClient.http_put(url, bPrint=False, body=body, body_type=body_type)
            elif method == 'DELETE':
                res = HttpClient.http_delete(url, bPrint=False, body=body, body_type=body_type)
            else:
                raise ValueError(f"Unsupported method: {method}")

            http_status = res.status_code if res else 0
            response_json = json.loads(res.text) if res else {}
            success = (res is not None and res.status_code == case.expected_status)
            error_info = ''
            if not success:
                error_info = f'HTTP status {http_status} != {case.expected_status}'
            else:
                # 断言
                assertions = case.assertions or []
                for assertion in assertions:
                    ok, msg = AssertionEngine.assert_one(assertion, response_json, context)
                    if not ok:
                        success = False
                        error_info += msg + "; "
                # 提取变量
                if case.extract:
                    extracted = Extractor.extract(response_json, case.extract, context=context)
                    context.set_by_path(f"steps.{case.name}", extracted)
            response_body = res.text if res else ''
        elif case.test_type == 'compare':
            host_old = host
            host_new = host_compare if host_compare is not None else host
            # 构造两个 URL（使用相同的 query_str）
            url_old = HttpClient.makeHttpUrl(host_old, api.path, query_str)
            url_new = HttpClient.makeHttpUrl(host_new, api.path, query_str)
            print("url_old", url_old)
            print("url_new", url_new)
            # 调用对比工具
            lsIgnore = []  # 可配置忽略字段
            if method == 'GET':
                lsTestLogInfo, result = compare_test_common.compare_url_get(url_old, url_new, case.name, lsIgnore)
            elif method == 'POST':
                lsTestLogInfo, result = compare_test_common.compare_url_post(url_old, url_new, case.name, lsIgnore,
                                                                             post_body=body, body_type=body_type)
            elif method in ['PUT', 'DELETE']:
                # 暂用 post 版本（只关心响应体）
                lsTestLogInfo, result = compare_test_common.compare_url_post(url_old, url_new, case.name, lsIgnore,
                                                                             post_body=body, body_type=body_type)
            else:
                raise ValueError(f"Unsupported method for compare test: {method}")

            success = result
            error_info = '' if success else '对比测试失败，详见日志'
            http_status = None  # 对比测试不单独记录状态码
            response_body = ''
        else:
            # 其他类型暂不支持
            success = False
            error_info = f'Unsupported test type: {case.test_type}'
            http_status = None
            response_body = ''
    except Exception as e:
        success = False
        error_info = f'Execution exception: {str(e)}'
        http_status = None
        response_body = ''
    finally:
        end = time.time()
        duration = int((end - start) * 1000)

    # 记录结果
    result_record = TestResult(
        case_id=case_id,
        run_id=run_id,
        status='success' if success else 'fail',
        http_status=http_status,
        response_body=response_body[:65535] if response_body else None,  # 截断避免过长
        error_info=error_info,
        start_time=datetime.fromtimestamp(start),
        end_time=datetime.fromtimestamp(end),
        duration_ms=duration
    )
    db.session.add(result_record)
    db.session.commit()

    return {
        'case_id': case_id,
        'status': result_record.status,
        'http_status': http_status,
        'error_info': error_info,
        'duration_ms': duration
    }


@run_bp.route('/testcase/<int:case_id>', methods=['POST'])
@require_permissions('run:execute')
def run_single(case_id):
    data = request.get_json() or {}
    host = data.get('host', current_app.config.get('DEFAULT_HOST', '172.17.12.101:9500'))
    run_id = str(uuid.uuid4())
    host_compare = data.get('host_compare', None)
    result = execute_case(case_id, host, run_id, host_compare=host_compare)
    result['run_id'] = run_id
    return jsonify(result)


@run_bp.route('/suite', methods=['POST'])
@require_permissions('run:execute')
def run_suite():
    data = request.get_json()
    if not data or 'case_ids' not in data:
        return jsonify({'error': 'case_ids required'}), 400
    case_ids = data['case_ids']
    host = data.get('host', current_app.config.get('DEFAULT_HOST', '172.17.12.101:9500'))
    host_compare = data.get('host_compare', None)
    loop_times = data.get('loop_times', 1)  # 支持多次循环
    run_id = str(uuid.uuid4())
    all_results = []
    for i in range(loop_times):
        for cid in case_ids:
            res = execute_case(cid, host, run_id, host_compare=host_compare)
            all_results.append(res)
    return jsonify({'run_id': run_id, 'results': all_results})


@run_bp.route('/results/<run_id>', methods=['GET'])
@require_permissions('run:read')
def get_results(run_id):
    results = TestResult.query.filter_by(run_id=run_id).all()
    return jsonify([{
        'case_id': r.case_id,
        'status': r.status,
        'http_status': r.http_status,
        'error_info': r.error_info,
        'duration_ms': r.duration_ms,
        'start_time': r.start_time.isoformat() if r.start_time else None
    } for r in results])


@run_bp.route('/records', methods=['GET'])
@require_permissions('run:read')
def list_run_records():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    run_id = request.args.get('run_id')
    record_type = request.args.get('type')       # testcase / flow
    target_id = request.args.get('target_id')    # case_id 或 flow_id
    status = request.args.get('status')          # success/fail/error/running

    all_records = []

    # 用例记录
    if not record_type or record_type == 'testcase':
        query = TestResult.query
        if run_id:
            query = query.filter(TestResult.run_id.like(f'%{run_id}%'))
        if target_id:
            query = query.filter_by(case_id=target_id)
        if status:
            query = query.filter_by(status=status)
        for r in query.all():
            all_records.append({
                'type': 'testcase',
                'id': r.id,
                'run_id': r.run_id,
                'case_id': r.case_id,
                'status': r.status,
                'http_status': r.http_status,
                'error_info': r.error_info,
                'start_time': r.start_time,
                'end_time': r.end_time,
                'duration_ms': r.duration_ms,
            })

    # 流程记录
    if not record_type or record_type == 'flow':
        query = FlowRun.query
        if run_id:
            query = query.filter(FlowRun.run_id.like(f'%{run_id}%'))
        if target_id:
            query = query.filter_by(flow_id=target_id)
        if status:
            query = query.filter_by(status=status)
        for r in query.all():
            error_info = r.error_info
            # 如果流程失败但 error_info 为空，从步骤中获取
            if r.status == 'fail' and not error_info:
                fail_steps = FlowStepResult.query.filter_by(flow_run_id=r.id, status='fail').all()
                if fail_steps:
                    errors = []
                    for step in fail_steps:
                        step_name = step.step_name or f"步骤{step.step_index+1}" if step.step_index is not None else "未知步骤"
                        err_msg = step.error_info or "未知错误"
                        errors.append(f"{step_name}: {err_msg}")
                    error_info = '；'.join(errors)
            all_records.append({
                'type': 'flow',
                'id': r.id,
                'run_id': r.run_id,
                'flow_id': r.flow_id,
                'status': r.status,
                'error_info': error_info,
                'start_time': r.start_time,
                'end_time': r.end_time,
                'duration_ms': r.duration_ms,
                'http_status': None,
            })

    # 按开始时间倒序
    from datetime import datetime
    all_records.sort(key=lambda x: x['start_time'] or datetime.min, reverse=True)
    total = len(all_records)
    start = (page - 1) * page_size
    end = start + page_size
    items = all_records[start:end]

    # 格式化时间
    for item in items:
        if item['start_time']:
            item['start_time'] = item['start_time'].isoformat()
        if item['end_time']:
            item['end_time'] = item['end_time'].isoformat()

    return jsonify({
        'items': items,
        'total': total,
        'page': page,
        'page_size': page_size
    })


@run_bp.route('/cancel/<run_id>', methods=['POST'])
@require_permissions('run:execute')
def cancel_run(run_id):
    """手动终止运行中的任务（更新状态为 fail）"""
    # 处理用例运行记录
    case_result = TestResult.query.filter_by(run_id=run_id, status='running').first()
    if case_result:
        case_result.status = 'fail'
        case_result.error_info = '用户手动终止'
        case_result.end_time = datetime.utcnow()
        if case_result.start_time:
            case_result.duration_ms = int((case_result.end_time - case_result.start_time).total_seconds() * 1000)
        db.session.commit()
        return jsonify({'message': '用例运行已终止'})

    # 处理流程运行记录
    flow_run = FlowRun.query.filter_by(run_id=run_id, status='running').first()
    if flow_run:
        flow_run.status = 'fail'
        flow_run.error_info = '用户手动终止'
        flow_run.end_time = datetime.utcnow()
        if flow_run.start_time:
            flow_run.duration_ms = int((flow_run.end_time - flow_run.start_time).total_seconds() * 1000)
        db.session.commit()
        return jsonify({'message': '流程运行已终止'})

    return jsonify({'error': '未找到运行中的记录'}), 404