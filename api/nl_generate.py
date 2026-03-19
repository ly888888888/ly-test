import json
import os
import re
import platform
from datetime import datetime
from genson import SchemaBuilder
from flask import Blueprint, request, jsonify
from api.auth import require_permissions
from models import ApiDefinition

nl_bp = Blueprint('nl_generate', __name__)


def extract_project(text):
    match = re.search(r'(\w+?)项目', text)
    return match.group(1) if match else 'edubox'


def extract_path_and_query(text):
    match = re.search(r'(/[^\s?]+)(\?[^\s]+)?', text)
    if not match:
        return None, {}
    path = match.group(1)
    query_str = match.group(2)[1:] if match.group(2) else ''
    query = {}
    if query_str:
        for pair in query_str.split('&'):
            if '=' in pair:
                k, v = pair.split('=', 1)
                query[k] = v
    return path, query


def _normalize_path(raw_path):
    if not raw_path:
        return raw_path
    return raw_path.split('?', 1)[0]


def project_exists(project):
    return ApiDefinition.query.filter_by(project=project).first() is not None


def interface_exists(project, path, method):
    return ApiDefinition.query.filter_by(project=project, path=path, method=method).first() is not None


def extract_method(text):
    if 'POST请求' in text:
        return 'POST'
    if 'PUT请求' in text:
        return 'PUT'
    if 'DELETE请求' in text:
        return 'DELETE'
    return 'GET'


def extract_response_json(text):
    keys = ['返回结果', '接口请求返回结果', '响应', 'response']
    start = -1
    for k in keys:
        idx = text.find(k)
        if idx != -1:
            start = text.find('{', idx)
            break
    if start == -1:
        start = text.find('{')
    if start == -1:
        return None
    stack = 0
    end = start
    for i, ch in enumerate(text[start:], start=start):
        if ch == '{':
            stack += 1
        elif ch == '}':
            stack -= 1
        if stack == 0:
            end = i
            break
    json_str = text[start:end + 1]
    try:
        return json.loads(json_str)
    except Exception:
        return None


def generate_schema(json_obj):
    builder = SchemaBuilder()
    builder.add_object(json_obj)
    schema = builder.to_schema()
    if '$schema' not in schema:
        schema['$schema'] = 'http://json-schema.org/draft-07/schema#'
    return schema


def _parse_param_value(value_str):
    if value_str.startswith('"') and value_str.endswith('"'):
        value_str = value_str[1:-1]
    if value_str.startswith("'") and value_str.endswith("'"):
        value_str = value_str[1:-1]

    match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\(\)$', value_str)
    if match:
        func_name = match.group(1)
        return ('function', func_name)

    match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\((.*)\)$', value_str, re.DOTALL)
    if match:
        func_name = match.group(1)
        args_str = match.group(2).strip()
        args = {}
        if args_str:
            for arg_part in args_str.split(','):
                arg_part = arg_part.strip()
                if '=' in arg_part:
                    arg_name, arg_value = arg_part.split('=', 1)
                    arg_name = arg_name.strip()
                    arg_value = arg_value.strip()
                    if arg_value.isdigit():
                        arg_value = int(arg_value)
                    elif (arg_value.startswith('"') and arg_value.endswith('"')) or \
                         (arg_value.startswith("'") and arg_value.endswith("'")):
                        arg_value = arg_value[1:-1]
                    args[arg_name] = arg_value
                else:
                    raise ValueError(f"位置参数不支持，请使用命名参数格式：{func_name}(arg1=value)")
        return ('function_with_args', (func_name, args))

    if re.search(r'SELECT\s+.*\s+FROM', value_str, re.IGNORECASE):
        return ('db_query', value_str)

    return ('fixed', value_str)


def query_to_params(query_dict):
    params = {}
    for key, value_str in query_dict.items():
        typ, val = _parse_param_value(value_str)
        if typ == 'fixed':
            params[key] = {"type": "fixed", "value": val}
        elif typ == 'function':
            params[key] = {"type": "function", "function": val, "args": {}}
        elif typ == 'function_with_args':
            func_name, args = val
            params[key] = {"type": "function", "function": func_name, "args": args}
        elif typ == 'db_query':
            params[key] = {"type": "db_query", "sql": val}
    return params


def save_json(payload, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def get_line_break():
    return "^" if platform.system() == "Windows" else "\\"


def generate_interface_payload(project, path, method, schema, description):
    return {
        "project": project,
        "path": path,
        "method": method,
        "schema": schema,
        "description": description
    }


def generate_interface_curl(base_url, payload, safe_path, out_dir):
    filename = f"interface_{safe_path}.json"
    save_json(payload, os.path.join(out_dir, filename))
    lb = get_line_break()
    return f"""
# 创建接口
curl -s -w \\\"\\nHTTP_STATUS:%{{http_code}}\\n\\\" -X POST {base_url}/api/interfaces {lb}
-H \\\"Content-Type: application/json\\\" {lb}
-d @{filename}
"""


def generate_testcase_payload(project, test_type, name_suffix, params, api_id_placeholder=0, assertions=None, expected_status=None):
    payload = {
        "project": project,
        "name": name_suffix,
        "api_id": api_id_placeholder,
        "test_type": test_type,
        "params": params,
        "enabled": True
    }
    if assertions:
        payload["assertions"] = assertions
    if expected_status is not None:
        payload["expected_status"] = expected_status
    return payload


def generate_testcase_curl(base_url, payload, safe_path, test_type, out_dir):
    filename = f"testcase_{safe_path}_{test_type}.json"
    save_json(payload, os.path.join(out_dir, filename))
    lb = get_line_break()
    return f"""
curl -s -w \\\"\\nHTTP_STATUS:%{{http_code}}\\n\\\" -X POST {base_url}/api/testcases {lb}
-H \\\"Content-Type: application/json\\\" {lb}
-d @{filename}
"""


def generate_flow_curl(base_url, flow_name, steps, out_dir, data_source=None, enabled=True):
    payload = {
        "name": flow_name,
        "steps": steps,
        "enabled": enabled
    }
    if data_source is not None:
        payload["data_source"] = data_source
    filename = f"flow_{flow_name}.json".replace(' ', '_')
    save_json(payload, os.path.join(out_dir, filename))
    lb = get_line_break()
    return f"""
# 创建测试流程
curl -s -w \\\"\\nHTTP_STATUS:%{{http_code}}\\n\\\" -X POST {base_url}/api/flows {lb}
-H \\\"Content-Type: application/json\\\" {lb}
-d @{filename}
"""


def extract_requested_tests(text):
    if re.search(r'只(?:创建|生成)?接口|仅接口', text):
        return []
    mapping = {
        'smoke': ['smoke', '冒烟测试', '冒烟'],
        'structural': ['structural', '结构测试', '结构'],
        'logic': ['logic', '逻辑测试', '逻辑'],
        'compare': ['compare', '对比测试', '对比'],
        'monitor': ['monitor', '监控测试', '监控'],
    }
    found = set()
    for key, keywords in mapping.items():
        for kw in keywords:
            if kw in text:
                found.add(key)
                break
    return list(found) if found else None


def has_explicit_test_request(text):
    return re.search(r'需要生成|生成(?:.*)?测试|创建(?:.*)?测试|生成用例|测试用例', text) is not None


def _extract_steps_from_text(text):
    step_pattern = re.compile(r'(\d+(?:\.\d+)*)\)\s*(GET|POST|PUT|DELETE)\s+([^\s]+)', re.IGNORECASE)
    matches = list(step_pattern.finditer(text))
    if not matches:
        return []
    steps = []
    for idx, m in enumerate(matches):
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        block = text[start:end]
        req_match = re.search(r'请求[:：]\\s*(\\{[\\s\\S]*?\\})(?=\\n|\\r|$)', block)
        resp_match = re.search(r'响应[:：]\\s*(\\{[\\s\\S]*?\\}|\\[[\\s\\S]*?\\])(?=\\n|\\r|$)', block)
        req_json = None
        resp_json = None
        if req_match:
            try:
                req_json = json.loads(req_match.group(1))
            except Exception:
                req_json = None
        if resp_match:
            try:
                resp_json = json.loads(resp_match.group(1))
            except Exception:
                resp_json = None
        steps.append({
            "index": m.group(1),
            "method": m.group(2).upper(),
            "path": m.group(3),
            "request": req_json,
            "response": resp_json
        })
    return steps


def _extract_flow_with_condition(text):
    cond_match = re.search(r'IF\s*条件[:：]\s*(.+)', text)
    if not cond_match:
        return []
    cond_expr = cond_match.group(1).strip()
    then_idx = text.find('THEN', cond_match.end())
    if then_idx == -1:
        return []
    else_idx = text.find('ELSE', then_idx)
    pre_text = text[:cond_match.start()]
    if else_idx == -1:
        then_text = text[then_idx:]
        else_text = ''
        post_text = ''
    else:
        then_text = text[then_idx:else_idx]
        else_text = text[else_idx:]
        post_text = ''
    pre_steps = _extract_steps_from_text(pre_text)
    then_steps = _extract_steps_from_text(then_text)
    else_steps = _extract_steps_from_text(else_text)
    flow_items = []
    flow_items.extend(pre_steps)
    flow_items.append({
        "type": "condition",
        "if": cond_expr,
        "then": then_steps,
        "else": else_steps
    })
    if post_text:
        flow_items.extend(_extract_steps_from_text(post_text))
    return flow_items


def _extract_simple_extracts(resp_json):
    extracts = {}
    if isinstance(resp_json, dict):
        for k, v in resp_json.items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                extracts[k] = f"$.{k}"
    return extracts


def build_flow_steps(parsed_steps, prev_extracted=None):
    flow_steps = []
    prev_extracted = prev_extracted or {}
    for i, step in enumerate(parsed_steps, start=1):
        if isinstance(step, dict) and step.get("type") == "condition":
            then_built = build_flow_steps(step.get("then", []), prev_extracted.copy())
            else_built = build_flow_steps(step.get("else", []), prev_extracted.copy())
            flow_steps.append({
                "type": "condition",
                "if": step.get("if"),
                "then": then_built,
                "else": else_built
            })
            continue

        name = f"step{i}"
        raw_req = step["request"] if isinstance(step["request"], dict) else {}
        params = raw_req.get("params") if "params" in raw_req else raw_req
        assertions = raw_req.get("assertions")
        extract = raw_req.get("extract")

        if isinstance(params, dict):
            for k, v in list(params.items()):
                for ex_key, ex_val in prev_extracted.items():
                    if v == ex_val:
                        params[k] = f"${{{ex_key}}}"

        extracts = extract if extract is not None else (_extract_simple_extracts(step["response"]) if step["response"] is not None else {})
        for ex_key in extracts.keys():
            prev_extracted[f"steps.{name}.{ex_key}"] = step["response"].get(ex_key) if isinstance(step["response"], dict) else None

        flow_steps.append({
            "type": "step",
            "name": name,
            "api_id": "{接口ID_" + name + "}",
            "params": params if isinstance(params, dict) else {},
            "assertions": assertions if assertions else None,
            "extract": extracts if extracts else None
        })

    for s in flow_steps:
        if s.get("extract") is None:
            s.pop("extract", None)
        if s.get("assertions") is None:
            s.pop("assertions", None)
    return flow_steps


def is_new_interface(text):
    return re.search(r'新接口|新增接口', text) is not None


def is_only_create_interface(text):
    return re.search(r'只(?:创建|生成)?接口|仅接口', text) is not None


def _normalize_operator(op):
    mapping = {
        '==': 'eq', '!=': 'ne', '>=': 'ge', '<=': 'le', '>': 'gt', '<': 'lt',
        '等于': 'eq', '不等于': 'ne', '大于等于': 'ge', '小于等于': 'le', '大于': 'gt', '小于': 'lt'
    }
    return mapping.get(op, op)


def _parse_value(val_str):
    val_str = val_str.strip()
    if (val_str.startswith('"') and val_str.endswith('"')) or (val_str.startswith("'") and val_str.endswith("'")):
        return val_str[1:-1]
    if re.match(r'^-?\d+(\.\d+)?$', val_str):
        return int(val_str) if val_str.isdigit() else float(val_str)
    return val_str


def parse_assertion_expr(expr):
    expr = expr.strip()
    op_order = ['大于等于', '小于等于', '不等于', '等于', '>=', '<=', '!=', '==', '>', '<', '大于', '小于']
    for op in op_order:
        if op in expr:
            left, right = expr.split(op, 1)
            return {
                "type": "path",
                "path": left.strip(),
                "operator": _normalize_operator(op),
                "value": _parse_value(right.strip())
            }
    return None


def _extract_assertion_texts(text, keywords):
    results = []
    for kw in keywords:
        pattern = rf'{kw}断言(?:是|为)?[:：,，]?\s*([^\n。；;]+)'
        matches = re.findall(pattern, text)
        for m in matches:
            results.append(m.strip())
    return results


def extract_assertions(text, test_type):
    keyword_map = {
        'smoke': ['smoke', '冒烟', '冒烟测试'],
        'structural': ['structural', '结构', '结构测试'],
        'logic': ['logic', '逻辑', '逻辑测试'],
        'compare': ['compare', '对比', '对比测试'],
        'monitor': ['monitor', '监控', '监控测试'],
    }
    if test_type == 'logic':
        numbered = re.findall(r'第[一二三四五六七八九十\d]+个逻辑用例断言(?:是|为)?[:：,，]?\s*([^\n。；;]+)', text)
        if numbered:
            cases = []
            for expr in numbered:
                parts = [p.strip() for p in re.split(r'[、;；]', expr) if p.strip()]
                assertions = [parse_assertion_expr(p) for p in parts]
                assertions = [a for a in assertions if a]
                if assertions:
                    cases.append(assertions)
            return cases if cases else []
        exprs = _extract_assertion_texts(text, keyword_map['logic'])
        parts = []
        for expr in exprs:
            parts.extend([p.strip() for p in re.split(r'[、;；]', expr) if p.strip()])
        assertions = [parse_assertion_expr(p) for p in parts]
        assertions = [a for a in assertions if a]
        return [assertions] if assertions else []
    else:
        exprs = _extract_assertion_texts(text, keyword_map[test_type])
        parts = []
        for expr in exprs:
            parts.extend([p.strip() for p in re.split(r'[、;；]', expr) if p.strip()])
        assertions = [parse_assertion_expr(p) for p in parts]
        return [a for a in assertions if a]


def extract_step_assertions(text):
    step_assertions = {}
    generic_matches = re.findall(r'步骤(\d+(?:\.\d+)*)断言(?:是|为)?[:：,，]?\s*([^\n。；;]+)', text)
    for step_idx, expr in generic_matches:
        parts = [p.strip() for p in re.split(r'[、;；]', expr) if p.strip()]
        assertions = [parse_assertion_expr(p) for p in parts]
        assertions = [a for a in assertions if a]
        if assertions:
            step_assertions.setdefault(step_idx, []).extend(assertions)
    keyword_map = {
        'logic': ['logic', '逻辑', '逻辑测试'],
        'smoke': ['smoke', '冒烟', '冒烟测试'],
        'structural': ['structural', '结构', '结构测试'],
        'compare': ['compare', '对比', '对比测试'],
        'monitor': ['monitor', '监控', '监控测试'],
    }
    for _, keywords in keyword_map.items():
        for kw in keywords:
            pattern = rf'步骤(\d+(?:\.\d+)*){kw}断言(?:是|为)?[:：,，]?\s*([^\n。；;]+)'
            matches = re.findall(pattern, text)
            for step_idx, expr in matches:
                parts = [p.strip() for p in re.split(r'[、;；]', expr) if p.strip()]
                assertions = [parse_assertion_expr(p) for p in parts]
                assertions = [a for a in assertions if a]
                if not assertions:
                    continue
                if step_idx in step_assertions:
                    step_assertions[step_idx].extend(assertions)
                else:
                    step_assertions[step_idx] = assertions
    return step_assertions


def apply_step_assertions(parsed_steps, step_assertions):
    for step in parsed_steps:
        if isinstance(step, dict) and step.get("type") == "condition":
            apply_step_assertions(step.get("then", []), step_assertions)
            apply_step_assertions(step.get("else", []), step_assertions)
            continue
        if not isinstance(step, dict):
            continue
        step_idx = step.get("index")
        if not step_idx:
            continue
        assertions = step_assertions.get(step_idx)
        if not assertions:
            continue
        if not isinstance(step.get("request"), dict):
            step["request"] = {}
        existing = step["request"].get("assertions")
        if isinstance(existing, list) and existing:
            step["request"]["assertions"] = existing + assertions
        else:
            step["request"]["assertions"] = assertions


def _collect_missing_interfaces(project, parsed_steps):
    missing = []

    def _walk(steps):
        for step in steps:
            if isinstance(step, dict) and step.get("type") == "condition":
                _walk(step.get("then", []))
                _walk(step.get("else", []))
                continue
            if not isinstance(step, dict):
                continue
            method = step.get("method")
            path = _normalize_path(step.get("path"))
            if not method or not path:
                continue
            if not interface_exists(project, path, method):
                missing.append({
                    "index": step.get("index"),
                    "method": method,
                    "path": path
                })

    _walk(parsed_steps)
    return missing


def _expected_example():
    return (
        "示例格式:\n"
        "/add-interface-curl-py 我现在有个新接口,GET请求,edubox项目,请求路由和参数:/edu/funclock/homepage/english?isencode=1,"
        "接口请求返回结果:{\"retCode\":\"200\",\"retMsg\":\"ok\",\"data\":[]}\n"
        "如果是流程，仍需包含返回结果块。"
    )


@nl_bp.route('/nl/generate', methods=['POST'])
@require_permissions(allow_anonymous=True)
def generate():
    data = request.get_json() or {}
    text = data.get('text', '')
    if not text:
        return jsonify({'error': 'text required', 'expected': _expected_example()}), 400

    project = extract_project(text)
    path, query = extract_path_and_query(text)
    if not path:
        return jsonify({'error': '未找到接口路径', 'expected': _expected_example()}), 400
    method = extract_method(text)

    has_flow = re.search(r'测试流程|多步流程|多步接口用例|流程步骤', text) is not None

    response_json = extract_response_json(text)
    if response_json is None and not has_flow:
        return jsonify({'error': '未找到返回JSON', 'expected': _expected_example()}), 400

    schema = generate_schema(response_json) if response_json is not None else {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object"
    }
    base_params = query_to_params(query)
    safe_path = path.lstrip('/').replace('/', '_')

    requested_tests = extract_requested_tests(text)
    if has_flow and not has_explicit_test_request(text):
        requested_tests = []
    elif requested_tests is None:
        if has_flow:
            requested_tests = []
        else:
            requested_tests = ['smoke', 'structural', 'logic', 'compare', 'monitor']

    create_interface = is_new_interface(text) or is_only_create_interface(text)

    if has_flow and re.search(r'IF\s*条件[:：]', text):
        parsed_steps = _extract_flow_with_condition(text)
    else:
        parsed_steps = _extract_steps_from_text(text) if has_flow else []
    step_assertions = extract_step_assertions(text)
    if parsed_steps and step_assertions:
        apply_step_assertions(parsed_steps, step_assertions)

    need_validation = has_flow or (requested_tests is not None and len(requested_tests) > 0)
    if need_validation and not project_exists(project):
        return jsonify({'error': f'项目不存在: {project}', 'expected': _expected_example()}), 400
    if has_flow and parsed_steps:
        missing = _collect_missing_interfaces(project, parsed_steps)
        if missing:
            details = "\n".join([f"步骤{m['index']} {m['method']} {m['path']}" for m in missing])
            return jsonify({'error': f'流程步骤接口不存在:\n{details}', 'expected': _expected_example()}), 400
    if not has_flow and requested_tests:
        main_path = _normalize_path(path)
        if not interface_exists(project, main_path, method):
            return jsonify({'error': f'接口不存在: {project} {method} {main_path}', 'expected': _expected_example()}), 400

    out_dir = os.path.join(os.getcwd(), 'generated')
    os.makedirs(out_dir, exist_ok=True)

    base_url = data.get('base_url') or request.host_url.rstrip('/')

    curl_parts = []

    interface_payload = generate_interface_payload(project, path, method, schema, f"自动创建接口: {path}")
    if create_interface:
        curl_parts.append(generate_interface_curl(base_url, interface_payload, safe_path, out_dir))
    else:
        interface_payload = None

    testcases = []
    flow_payload = None
    if requested_tests:
        if 'smoke' in requested_tests:
            smoke_assertions = extract_assertions(text, 'smoke')
            payload = generate_testcase_payload(project, 'smoke', f"{path} 冒烟测试", base_params, assertions=smoke_assertions or None, expected_status=200)
            testcases.append(payload)
            curl_parts.append(generate_testcase_curl(base_url, payload, safe_path, 'smoke', out_dir))
        if 'structural' in requested_tests:
            structural_assertions = extract_assertions(text, 'structural')
            payload = generate_testcase_payload(project, 'structural', f"{path} 结构测试", base_params, assertions=structural_assertions or None)
            testcases.append(payload)
            curl_parts.append(generate_testcase_curl(base_url, payload, safe_path, 'structural', out_dir))
        if 'logic' in requested_tests:
            logic_cases = extract_assertions(text, 'logic')
            if logic_cases and isinstance(logic_cases, list) and logic_cases and isinstance(logic_cases[0], list):
                for idx, assertions in enumerate(logic_cases, start=1):
                    payload = generate_testcase_payload(project, 'logic', f"{path} 逻辑测试{idx}", base_params, assertions=assertions)
                    testcases.append(payload)
                    curl_parts.append(generate_testcase_curl(base_url, payload, safe_path, f'logic{idx}', out_dir))
            else:
                payload = generate_testcase_payload(project, 'logic', f"{path} 逻辑测试", base_params)
                testcases.append(payload)
                curl_parts.append(generate_testcase_curl(base_url, payload, safe_path, 'logic', out_dir))
        if 'compare' in requested_tests:
            compare_assertions = extract_assertions(text, 'compare')
            payload = generate_testcase_payload(project, 'compare', f"{path} 对比测试", base_params, assertions=compare_assertions or None)
            testcases.append(payload)
            curl_parts.append(generate_testcase_curl(base_url, payload, safe_path, 'compare', out_dir))
        if 'monitor' in requested_tests:
            monitor_assertions = extract_assertions(text, 'monitor')
            payload = generate_testcase_payload(project, 'monitor', f"{path} 监控测试", base_params, assertions=monitor_assertions or None)
            testcases.append(payload)
            curl_parts.append(generate_testcase_curl(base_url, payload, safe_path, 'monitor', out_dir))

    if parsed_steps:
        flow_steps = build_flow_steps(parsed_steps)
        flow_name = f"flow_{safe_path}"
        flow_payload = {
            "name": flow_name,
            "steps": flow_steps,
            "enabled": True
        }
        curl_parts.append(generate_flow_curl(base_url, flow_name, flow_steps, out_dir))
        curl_parts.append("\n说明: flow steps 中 api_id 使用占位符 {接口ID_stepN}，请替换为对应接口定义ID\n")

    curl_text = "\n".join([p for p in curl_parts if p])
    txt_name = f"{safe_path}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.txt"
    with open(os.path.join(out_dir, txt_name), 'w', encoding='utf-8') as f:
        f.write(curl_text)

    return jsonify({
        'interfacePayload': interface_payload,
        'testcases': testcases,
        'flowPayload': flow_payload,
        'curl_text': curl_text,
        'files': {
            'txt': txt_name
        }
    })
