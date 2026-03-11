from dsl.context import Context
from dsl.extractor import Extractor
from dsl.assertion import AssertionEngine
from models import ApiDefinition
from tools.http_client import HttpClient, RAWJSON
from api.utils import resolve_params, resolve_variables
import json
from models import TestFlow

def execute_flow(flow_id, host, host_compare=None):
    flow = TestFlow.query.get(flow_id)
    if not flow or not flow.enabled:
        return {'error': 'Flow not found or disabled'}

    context = Context()
    results = []

    for step in flow.steps:
        api = ApiDefinition.query.get(step['api_id'])
        if not api:
            results.append({'step': step['name'], 'error': 'API not found'})
            break

        method = api.method.upper()
        # 解析参数（先处理函数、SQL等）
        raw_params = resolve_params(step['params'])
        # 应用变量引用（从上下文获取）
        final_params = resolve_variables(raw_params, context)

        # 构造请求
        if method == 'GET':
            query_str = HttpClient.querydict_to_querystr(final_params)
            url = HttpClient.makeHttpUrl(host, api.path, query_str)
            body = None
        else:
            query_str = ''
            url = HttpClient.makeHttpUrl(host, api.path, query_str)
            body = final_params

        # 发送请求
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
            results.append({'step': step['name'], 'error': f'Request failed: {str(e)}'})
            continue

        # 记录响应
        response_json = json.loads(res.text) if res else {}
        http_status = res.status_code if res else 0

        # 断言
        step_success = True
        error_msgs = []
        for assertion in step.get('assertions', []):
            ok, msg = AssertionEngine.assert_one(assertion, response_json, context)
            if not ok:
                step_success = False
                error_msgs.append(msg)

        # 提取变量
        if step.get('extract'):
            extracted = Extractor.extract(response_json, step['extract'])
            # 以步骤名存储
            context.set_by_path(f"steps.{step['name']}", extracted)

        results.append({
            'step': step['name'],
            'status': 'success' if step_success else 'fail',
            'http_status': http_status,
            'errors': error_msgs,
            'extracted': extracted if step.get('extract') else {}
        })

    return {'flow_id': flow_id, 'results': results}