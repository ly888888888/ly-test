import json
import re
from datetime import datetime
from genson import SchemaBuilder
from flask import Blueprint, request, jsonify
from api.auth import require_permissions
from models import ApiDefinition, Project

nl_bp = Blueprint('nl_generate', __name__)

def _get_api_id_by_method_path(method, path, project_id):
    """根据 method、path 和项目 ID 查询接口的真实 ID"""
    normalized_path = _normalize_path(path)
    api = ApiDefinition.query.filter_by(
        project_id=project_id,
        method=method,
        path=normalized_path
    ).first()
    if api:
        return api.id
    else:
        return None

def extract_project(text):
    """提取项目名称，统一转为小写并去除首尾空格"""
    match = re.search(r'(\w+?)项目', text)
    if match:
        return match.group(1).strip().lower()
    # 也支持 "项目：xxx" 格式
    match = re.search(r'项目[:：]\s*([^\s,，]+)', text)
    if match:
        return match.group(1).strip().lower()
    return 'edubox'


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


def project_exists(project_name):
    """检查项目是否存在（忽略大小写）"""
    return Project.query.filter(Project.name.ilike(project_name)).first() is not None


def interface_exists(project_name, path, method):
    """检查接口是否存在（基于项目名称、路径、方法）"""
    project = Project.query.filter(Project.name.ilike(project_name)).first()
    if not project:
        return False
    return ApiDefinition.query.filter_by(project_id=project.id, path=path, method=method).first() is not None


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

    if value_str.startswith('template:'):
        template_name = value_str[9:].strip()
        return ('template', template_name)

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
        elif typ == 'template':  # 新增
            params[key] = {"type": "template", "name": val}
    return params


def generate_interface_payload(project, path, method, schema, description):
    return {
        "project": project,
        "path": path,
        "method": method,
        "schema": schema,
        "description": description
    }


def generate_testcase_payload(project, test_type, name_suffix, params, api_id, assertions=None, expected_status=None):
    payload = {
        "project": project,
        "name": name_suffix,
        "api_id": api_id,
        "test_type": test_type,
        "params": params,
        "enabled": True
    }
    if assertions:
        payload["assertions"] = assertions
    if expected_status is not None:
        payload["expected_status"] = expected_status
    return payload


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

        raw_path = m.group(3)
        path, query_dict = extract_path_and_query(raw_path)
        if not path:
            path = raw_path.split('?')[0]
        params = query_to_params(query_dict) if query_dict else {}

        # 解析请求体（可选）
        req_match = re.search(r'请求[:：]\s*(\{[^{}]*\})', block, re.DOTALL)
        req_json = None
        if req_match:
            try:
                req_json = json.loads(req_match.group(1))
            except Exception:
                req_json = None
        if req_json and isinstance(req_json, dict):
            if 'params' in req_json:
                params.update(req_json['params'])
            else:
                params.update(req_json)

        # 解析响应体
        resp_match = re.search(r'响应[:：]\s*(\{[^{}]*\}|\[.*?\])', block, re.DOTALL)
        resp_json = None
        if resp_match:
            try:
                resp_json = json.loads(resp_match.group(1))
            except Exception:
                resp_json = None

        # 解析提取规则
        extract_match = re.search(r'提取[:：]\s*(\{[^{}]*\})', block, re.DOTALL)
        extract = None
        if extract_match:
            try:
                extract = json.loads(extract_match.group(1))
            except Exception:
                extract = None

        # ========== 关键修改：解析断言 ==========
        assertion_match = re.search(r'断言[:：]\s*(.+?)(?=\n\s*\d+\)|\n\s*\n|$)', block, re.DOTALL)
        assertions = None
        if assertion_match:
            assertion_text = assertion_match.group(1).strip()
            parsed = parse_assertion_expr(assertion_text)
            if parsed:
                if isinstance(parsed, list):
                    assertions = parsed  # AND 组，多个断言
                elif isinstance(parsed, dict) and parsed.get('type') == 'or':
                    assertions = [parsed]  # OR 组，单个特殊断言
                else:
                    assertions = [parsed]  # 单个普通断言
        steps.append({
            "index": m.group(1),
            "method": m.group(2).upper(),
            "path": path,
            "request": {"params": params},
            "response": resp_json,
            "extract": extract,
            "assertions": assertions
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


def build_flow_steps(parsed_steps, project_id, prev_extracted=None):
    flow_steps = []
    prev_extracted = prev_extracted or {}
    for i, step in enumerate(parsed_steps, start=1):
        if isinstance(step, dict) and step.get("type") == "condition":
            then_built = build_flow_steps(step.get("then", []), project_id, prev_extracted.copy())
            else_built = build_flow_steps(step.get("else", []), project_id, prev_extracted.copy())
            flow_steps.append({
                "type": "condition",
                "if": step.get("if"),
                "then": then_built,
                "else": else_built
            })
            continue

        name = f"step{i}"
        params = step.get("request", {}).get("params", {})
        assertions = step.get("assertions")          # 直接使用解析到的断言
        extract = step.get("extract")

        # 处理参数中的变量引用
        if isinstance(params, dict):
            for k, v in list(params.items()):
                if isinstance(v, str) and v.startswith('${') and v.endswith('}'):
                    continue
                elif isinstance(v, dict):
                    pass
                else:
                    for ex_key, ex_val in prev_extracted.items():
                        if v == ex_val:
                            params[k] = f"${{{ex_key}}}"

        extracts = extract if extract else (_extract_simple_extracts(step["response"]) if step["response"] is not None else {})
        for ex_key in extracts.keys():
            prev_extracted[f"steps.{name}.{ex_key}"] = None

        step_obj = {
            "type": "step",
            "name": name,
            "api_id": _get_api_id_by_method_path(step.get("method"), step.get("path"), project_id),
            "params": params,
            "extract": extracts if extracts else None,
        }
        if assertions:
            step_obj["assertions"] = assertions

        flow_steps.append(step_obj)

    # 清理空字段
    for s in flow_steps:
        if s.get("extract") is None:
            s.pop("extract", None)
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
    """解析断言表达式，支持“且”、“或”及单个条件，返回断言对象或列表或 OR 组字典"""
    expr = expr.strip()

    # 处理“或”（OR 组）
    if '或' in expr:
        parts = expr.split('或')
        or_assertions = []
        for part in parts:
            part = part.strip()
            if part:
                # 递归解析每个部分（可能包含“且”）
                sub = parse_assertion_expr(part)
                if sub:
                    if isinstance(sub, list):
                        # 如果子部分是 AND 组，直接展开？不，OR 组内应保持 AND 组作为整体
                        # 简单起见，将 AND 组作为一个列表存入 OR 组
                        or_assertions.append(sub)
                    elif isinstance(sub, dict) and sub.get('type') == 'or':
                        # 避免嵌套 OR，展平（可选）
                        or_assertions.extend(sub.get('assertions', []))
                    else:
                        or_assertions.append(sub)
        if or_assertions:
            return {"type": "or", "assertions": or_assertions}

    # 处理“且”（AND 组，返回列表）
    if '且' in expr:
        parts = expr.split('且')
        and_assertions = []
        for part in parts:
            part = part.strip()
            if part:
                sub = parse_assertion_expr(part)
                if sub:
                    if isinstance(sub, list):
                        and_assertions.extend(sub)
                    elif isinstance(sub, dict) and sub.get('type') == 'or':
                        # OR 组作为整体放入 AND 组
                        and_assertions.append(sub)
                    else:
                        and_assertions.append(sub)
        return and_assertions if and_assertions else None

    # 单个断言
    return parse_single_assertion(expr)


def parse_single_assertion(expr):
    """解析单个断言条件，支持：不为空、为空、存在、不存在、比较运算符"""
    expr = expr.strip()

    # 1. 不为空 -> path ne null
    if '不为空' in expr:
        match = re.match(r'^(.+?)不为空$', expr)
        if match:
            path = match.group(1).strip()
            return {"type": "path", "path": path, "operator": "ne", "value": None}

    # 2. 为空 -> path eq null
    if '为空' in expr:
        match = re.match(r'^(.+?)为空$', expr)
        if match:
            path = match.group(1).strip()
            return {"type": "path", "path": path, "operator": "eq", "value": None}

    # 3. 存在 -> jsonpath exists true
    if '存在' in expr and '不' not in expr:
        match = re.match(r'^(.+?)存在$', expr)
        if match:
            path_expr = match.group(1).strip()
            jsonpath = path_expr if path_expr.startswith('$') else f"$.{path_expr}"
            return {"type": "jsonpath", "jsonpath": jsonpath, "operator": "exists", "value": True}

    # 4. 不存在 -> jsonpath exists false
    if '不存在' in expr:
        match = re.match(r'^(.+?)不存在$', expr)
        if match:
            path_expr = match.group(1).strip()
            jsonpath = path_expr if path_expr.startswith('$') else f"$.{path_expr}"
            return {"type": "jsonpath", "jsonpath": jsonpath, "operator": "exists", "value": False}

    # 5. 比较运算符（包括中文和符号）
    op_map = {
        '大于等于': 'ge', '小于等于': 'le', '不等于': 'ne', '等于': 'eq',
        '>=': 'ge', '<=': 'le', '!=': 'ne', '==': 'eq',
        '>': 'gt', '<': 'lt', '大于': 'gt', '小于': 'lt'
    }
    for op_text, op_code in op_map.items():
        if op_text in expr:
            left, right = expr.split(op_text, 1)
            return {
                "type": "path",
                "path": left.strip(),
                "operator": op_code,
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
    # 新增：尝试提取通用自然语言断言（格式：断言: ...）
    general_match = re.search(r'断言[:：]\s*(.+?)(?=\n|$)', text)
    if general_match:
        expr = general_match.group(1).strip()
        result = parse_assertion_expr(expr)
        if result:
            # 如果是列表，直接返回；否则包装为列表
            if isinstance(result, list):
                return result
            elif result:
                return [result]

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
        "我现在有个接口,GET请求,edubox项目,请求路由和参数:/edu/funclock/homepage/english?isencode=1,"
        "如果是流程，仍需包含返回结果块。"
    )


@nl_bp.route('/nl/generate', methods=['POST'])
@require_permissions(allow_anonymous=True)
def generate():
    data = request.get_json() or {}
    text = data.get('text', '')
    mode = data.get('mode', 'testcase')  # interface, testcase, flow
    if not text:
        return jsonify({'error': 'text required', 'expected': _expected_example()}), 400

    project = extract_project(text).strip().lower()
    project_obj = Project.query.filter(Project.name.ilike(project)).first()
    if not project_obj:
        return jsonify({
            'error': f'项目 "{project}" 不存在，请先创建项目',
            'code': 'PROJECT_NOT_FOUND'
        }), 400
    if not project_obj.enabled:
        return jsonify({
            'error': f'项目 "{project}" 已被禁用，无法使用',
            'code': 'PROJECT_DISABLED'
        }), 400

    path, query = extract_path_and_query(text)
    if not path:
        return jsonify({'error': '未找到接口路径', 'expected': _expected_example()}), 400
    method = extract_method(text)

    # 根据模式决定流程标志和响应 JSON 要求
    if mode == 'flow':
        has_flow = True
        response_json = extract_response_json(text)  # 可选
    elif mode == 'interface':
        has_flow = False
        response_json = extract_response_json(text) or {}  # 接口模式必须提供响应，否则用空对象（会报错但后续会提示）
    else:  # testcase
        has_flow = re.search(r'测试流程|多步流程|多步接口用例|流程步骤', text) is not None
        response_json = extract_response_json(text)  # 可选，不再强制要求

    # 生成 schema（若没有响应 JSON 则使用空对象）
    schema = generate_schema(response_json) if response_json else {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object"
    }
    base_params = query_to_params(query)
    safe_path = path.lstrip('/').replace('/', '_')

    # 根据模式处理
    if mode == 'interface':
        create_interface = True
        requested_tests = []
        parsed_steps = []
    elif mode == 'flow':
        create_interface = False
        requested_tests = []
        # 解析流程步骤
        if re.search(r'IF\s*条件[:：]', text):
            parsed_steps = _extract_flow_with_condition(text)
        else:
            parsed_steps = _extract_steps_from_text(text) if has_flow else []
        step_assertions = extract_step_assertions(text)
        if parsed_steps and step_assertions:
            apply_step_assertions(parsed_steps, step_assertions)
    else:  # testcase
        requested_tests = extract_requested_tests(text)
        if has_flow and not has_explicit_test_request(text):
            requested_tests = []
        elif requested_tests is None:
            if has_flow:
                requested_tests = []
            else:
                requested_tests = ['smoke', 'structural', 'logic', 'compare', 'monitor']
        create_interface = is_new_interface(text) or is_only_create_interface(text)
        parsed_steps = []

    # 接口存在性校验（仅 testcase 和 flow 需要）
    if mode == 'testcase':
        main_path = _normalize_path(path)
        if not interface_exists(project, main_path, method):
            return jsonify({'error': f'接口不存在: {project} {method} {main_path}，请先创建接口', 'expected': _expected_example()}), 400
    elif mode == 'flow' and parsed_steps:
        missing = _collect_missing_interfaces(project, parsed_steps)
        if missing:
            details = "\n".join([f"步骤{m['index']} {m['method']} {m['path']}" for m in missing])
            return jsonify({'error': f'流程步骤接口不存在:\n{details}', 'expected': _expected_example()}), 400

    # 查询真实接口 ID（用于 testcase）
    real_api_id = 0
    if mode == 'testcase' and requested_tests:
        main_path = _normalize_path(path)
        api_def = ApiDefinition.query.filter_by(project_id=project_obj.id, path=main_path, method=method).first()
        if api_def:
            real_api_id = api_def.id
        else:
            print(f"Warning: 未找到接口 {project} {method} {main_path}，使用 api_id=0")

    # 构建返回数据
    interface_payload = None
    if create_interface:
        interface_payload = generate_interface_payload(project, path, method, schema, f"自动创建接口: {path}")

    testcases = []
    flow_payload = None

    if mode == 'testcase' and requested_tests:
        # 生成用例（使用现有的 base_params 和从文本中解析的断言）
        for test_type in requested_tests:
            assertions = extract_assertions(text, test_type)  # 从文本中解析断言
            # 生成用例名称后缀
            name_suffix = f"{path} {test_type}测试"
            payload = generate_testcase_payload(
                project, test_type, name_suffix,
                base_params, real_api_id,
                assertions=assertions if assertions else None,
                expected_status=200 if test_type == 'smoke' else None
            )
            testcases.append(payload)

    if mode == 'flow' and parsed_steps:
        try:
            flow_steps = build_flow_steps(parsed_steps, project_obj.id)
            flow_name = f"flow_{safe_path}"
            flow_payload = {
                "name": flow_name,
                "project": project_obj.name,
                "steps": flow_steps,
                "enabled": True
            }
        except ValueError as e:
            return jsonify({'error': str(e), 'expected': _expected_example()}), 400

    return jsonify({
        'interfacePayload': interface_payload,
        'testcases': testcases,
        'flowPayload': flow_payload
    })