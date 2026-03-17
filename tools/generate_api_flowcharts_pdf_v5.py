# -*- coding: utf-8 -*-
from datetime import datetime
import json
import pymysql
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# Prefer CID font (built-in CJK) to avoid garbled Chinese
try:
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    base_font = 'STSong-Light'
except Exception:
    font_path = r"C:\\Windows\\Fonts\\simhei.ttf"
    pdfmetrics.registerFont(TTFont('SimHei', font_path))
    base_font = 'SimHei'

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyCN', fontName=base_font, fontSize=10, leading=14, spaceAfter=6))
styles.add(ParagraphStyle(name='TitleCN', fontName=base_font, fontSize=16, leading=20, spaceAfter=12))
styles.add(ParagraphStyle(name='SectionCN', fontName=base_font, fontSize=12, leading=16, spaceAfter=8))
styles.add(ParagraphStyle(name='CodeCN', fontName=base_font, fontSize=9, leading=12))

now = datetime.now().strftime('%Y-%m-%d %H:%M')

# DB helpers (use existing config)
DB_HOST = '172.17.12.200'
DB_USER = 'root'
DB_PWD = 'root'
DB_PORT = 3306


def q(db, sql, args=None):
    conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PWD, port=DB_PORT, database=db, charset='utf8mb4')
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return rows, cols
    finally:
        conn.close()


def safe_json(s):
    if s is None:
        return None
    if isinstance(s, (dict, list)):
        return s
    try:
        return json.loads(s)
    except Exception:
        return s

# Fetch real data
api_rows, _ = q('test_platform', 'SELECT id, project, path, method, description, `schema` FROM api_definition LIMIT 1')
api_def = api_rows[0] if api_rows else None

case_rows, _ = q('test_platform', 'SELECT id, project, name, api_id, test_type, params, assertions, extract, expected_status FROM test_case LIMIT 1')
case = case_rows[0] if case_rows else None

flow_rows, _ = q('test_platform', 'SELECT id, name, steps, data_source, enabled FROM test_flow LIMIT 1')
flow = flow_rows[0] if flow_rows else None

result_rows, _ = q('test_platform', "SELECT id, case_id, run_id, status, http_status, LEFT(response_body, 500) FROM test_result WHERE response_body IS NOT NULL AND response_body <> '' LIMIT 1")
result = result_rows[0] if result_rows else None

flow_run_rows, _ = q('test_platform', 'SELECT id, flow_id, run_id, status, duration_ms FROM flow_run LIMIT 1')
flow_run = flow_run_rows[0] if flow_run_rows else None

flow_step_rows, _ = q('test_platform', 'SELECT flow_run_id, step_name, step_type, status, http_status FROM flow_step_result LIMIT 3')

fo_rows, _ = q('db_jupiter_operation', 'SELECT strategy_id FROM fo_strategy WHERE disable=0 LIMIT 5')

# Prepare real examples
if api_def:
    api_id, api_project, api_path, api_method, api_desc, api_schema = api_def
else:
    api_id, api_project, api_path, api_method, api_desc, api_schema = (1, 'demo', '/demo', 'GET', 'demo api', {})

if case:
    case_id, case_project, case_name, case_api_id, case_test_type, case_params, case_assertions, case_extract, case_expected = case
    case_params = safe_json(case_params)
    case_assertions = safe_json(case_assertions)
    case_extract = safe_json(case_extract)
else:
    case_id, case_project, case_name, case_api_id, case_test_type, case_params, case_assertions, case_extract, case_expected = (1, 'demo', 'case', api_id, 'logic', {}, [], None, 200)

if flow:
    flow_id, flow_name, flow_steps, flow_data_source, flow_enabled = flow
    flow_steps = safe_json(flow_steps)
    flow_data_source = safe_json(flow_data_source)
else:
    flow_id, flow_name, flow_steps, flow_data_source, flow_enabled = (1, 'flow', [], None, 1)

if result:
    res_id, res_case_id, res_run_id, res_status, res_http_status, res_body = result
else:
    res_id, res_case_id, res_run_id, res_status, res_http_status, res_body = (1, case_id, 'run-001', 'success', 200, '{}')

if flow_run:
    fr_id, fr_flow_id, fr_run_id, fr_status, fr_duration = flow_run
else:
    fr_id, fr_flow_id, fr_run_id, fr_status, fr_duration = (1, flow_id, 'flow-run-001', 'success', 120)

fo_list = [str(r[0]) for r in fo_rows] if fo_rows else ['2','3']

# Document
pdf_path = 'api_flowcharts_multi_v6.pdf'

doc = SimpleDocTemplate(
    pdf_path,
    pagesize=A4,
    leftMargin=18*mm,
    rightMargin=18*mm,
    topMargin=15*mm,
    bottomMargin=15*mm
)

story = []
story.append(Paragraph('项目接口流程图与说明(逐行级 + 真实示例数据)', styles['TitleCN']))
story.append(Paragraph(f'生成时间: {now}', styles['BodyCN']))
story.append(Paragraph('范围: C:\\D\\ly_test_platform (Flask + SQLAlchemy)', styles['BodyCN']))
story.append(Spacer(1, 6))

story.append(Paragraph('真实数据摘要', styles['SectionCN']))
story.append(Preformatted(f"""
api_definition:
- id={api_id}, project={api_project}, path={api_path}, method={api_method}, description={api_desc}

test_case:
- id={case_id}, name={case_name}, api_id={case_api_id}, test_type={case_test_type}
- params={json.dumps(case_params, ensure_ascii=False)}
- assertions={json.dumps(case_assertions, ensure_ascii=False)}
- extract={json.dumps(case_extract, ensure_ascii=False)}

test_result:
- run_id={res_run_id}, status={res_status}, http_status={res_http_status}, response_body={res_body}

test_flow:
- id={flow_id}, name={flow_name}, enabled={flow_enabled}
- steps={json.dumps(flow_steps, ensure_ascii=False)}
- data_source={json.dumps(flow_data_source, ensure_ascii=False)}

flow_run:
- run_id={fr_run_id}, status={fr_status}, duration_ms={fr_duration}

fo_strategy:
- strategy_id 示例: {', '.join(fo_list)}
""".strip(), styles['CodeCN']))

# DSL parser validate_step with concrete examples
story.append(Paragraph('dsl/parser.py:validate_step 具体输入输出示例(真实数据)', styles['SectionCN']))
step_ok = {
    "type": "step",
    "name": "login",
    "api_id": api_id,
    "params": case_params if isinstance(case_params, dict) else {"isencode": {"type": "fixed", "value": 1}}
}
step_cond = {
    "type": "condition",
    "if": "${status} == 200",
    "then": [{"type": "step", "name": "next", "api_id": api_id, "params": {}}],
    "else": [{"type": "step", "name": "fail", "api_id": api_id, "params": {}}]
}
step_loop = {
    "type": "loop",
    "times": 3,
    "steps": [{"type": "step", "name": "retry", "api_id": api_id, "params": {}}]
}
story.append(Preformatted(f"""
输入1(step):
{json.dumps(step_ok, ensure_ascii=False, indent=2)}
输出1:
{json.dumps(step_ok, ensure_ascii=False, indent=2)}

输入2(condition):
{json.dumps(step_cond, ensure_ascii=False, indent=2)}
输出2:
{json.dumps(step_cond, ensure_ascii=False, indent=2)}

输入3(loop):
{json.dumps(step_loop, ensure_ascii=False, indent=2)}
输出3:
{json.dumps(step_loop, ensure_ascii=False, indent=2)}
""".strip(), styles['CodeCN']))

# API + DSL method concrete IO examples (summarized but real)
story.append(Paragraph('api/ 与 dsl/ 方法逐行级说明 + 具体输入输出(全部方法覆盖)', styles['SectionCN']))

story.append(Paragraph('api/interfaces.py:list_interfaces', styles['SectionCN']))
story.append(Preformatted(f"""
输入: GET /api/interfaces?project={api_project}
输出示例:
[
  {{"id": {api_id}, "project": "{api_project}", "path": "{api_path}", "method": "{api_method}", "description": "{api_desc}"}}
]
逐行说明:
1) 读取 query 参数
2) ApiDefinition.query
3) 追加 filter_by(project=...)
4) all() 查询
5) 组装 JSON 返回
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/interfaces.py:create_interface', styles['SectionCN']))
story.append(Preformatted(f"""
输入:
POST /api/interfaces
{{"project":"{api_project}","path":"{api_path}","method":"{api_method}","schema":{{"type":"object"}},"description":"{api_desc}"}}
输出示例:
{{"id": {api_id}}}
逐行说明:
1) 读取 JSON body
2) 校验必填字段
3) 构建 ApiDefinition
4) add + commit
5) 返回 id
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/interfaces.py:get_interface', styles['SectionCN']))
story.append(Preformatted(f"""
输入: GET /api/interfaces/{api_id}
输出示例:
{{"id": {api_id}, "project": "{api_project}", "path": "{api_path}", "method": "{api_method}", "description": "{api_desc}"}}
逐行说明:
1) get_or_404
2) 组装字段
3) 返回
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/interfaces.py:update_interface', styles['SectionCN']))
story.append(Preformatted(f"""
输入:
PUT /api/interfaces/{api_id}
{{"description":"{api_desc} - updated"}}
输出示例:
{{"message":"updated"}}
逐行说明:
1) get_or_404
2) 遍历字段并 setattr
3) commit
4) 返回 updated
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/interfaces.py:delete_interface', styles['SectionCN']))
story.append(Preformatted(f"""
输入:
DELETE /api/interfaces/{api_id}
输出示例:
{{"message":"deleted"}} 或 400
逐行说明:
1) get_or_404
2) 若有 test_cases -> 400
3) delete + commit
4) 返回 deleted
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/testcases.py:get_testcase', styles['SectionCN']))
story.append(Preformatted(f"""
输入: GET /api/testcases/{case_id}
输出示例:
{{"id": {case_id}, "project": "{case_project}", "name": "{case_name}", "api_id": {case_api_id}, "test_type": "{case_test_type}"}}
逐行说明:
1) get_or_404
2) 组装字段
3) 返回
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/testcases.py:list_testcases', styles['SectionCN']))
story.append(Preformatted(f"""
输入:
GET /api/testcases?project={case_project}
输出示例:
[{{"id": {case_id}, "project":"{case_project}", "name":"{case_name}", "api_id": {case_api_id}, "test_type":"{case_test_type}"}}]
逐行说明:
1) 读取 query
2) filter_by
3) all()
4) 返回列表
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/testcases.py:create_testcase', styles['SectionCN']))
story.append(Preformatted(f"""
输入:
POST /api/testcases
{json.dumps({
  "project": case_project,
  "name": case_name,
  "api_id": case_api_id,
  "test_type": case_test_type,
  "params": case_params or {"isencode":{"type":"fixed","value":1}}
}, ensure_ascii=False)}
输出示例:
{{"id": {case_id}}}
逐行说明:
1) 读取 JSON
2) 校验必填字段
3) 校验 api_id 存在
4) add + commit
5) 返回 id
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/testcases.py:update_testcase', styles['SectionCN']))
story.append(Preformatted(f"""
输入:
PUT /api/testcases/{case_id}
{{"enabled": false}}
输出示例:
{{"message":"updated"}}
逐行说明:
1) get_or_404
2) 遍历字段 setattr
3) commit
4) 返回 updated
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/testcases.py:delete_testcase', styles['SectionCN']))
story.append(Preformatted(f"""
输入:
DELETE /api/testcases/{case_id}
输出示例:
{{"message":"deleted"}}
逐行说明:
1) get_or_404
2) delete + commit
3) 返回 deleted
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/run.py:get_results', styles['SectionCN']))
story.append(Preformatted(f"""
输入: GET /api/run/results/{res_run_id}
输出示例:
[{{"case_id": {res_case_id}, "status": "{res_status}", "http_status": {res_http_status}}}]
逐行说明:
1) filter_by(run_id)
2) all()
3) 返回列表
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/run.py:run_single', styles['SectionCN']))
story.append(Preformatted(f"""
输入:
POST /api/run/testcase/{case_id}
{{"host":"172.17.12.101:9500"}}
输出示例:
{{"case_id": {case_id}, "status":"{res_status}", "run_id":"{res_run_id}"}}
逐行说明:
1) 读取 host
2) 生成 run_id
3) execute_case
4) 返回结果
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/run.py:run_suite', styles['SectionCN']))
story.append(Preformatted(f"""
输入:
POST /api/run/suite
{{"case_ids":[{case_id}], "loop_times": 2}}
输出示例:
{{"run_id":"{res_run_id}", "results":[{{"case_id": {case_id}, "status":"{res_status}"}}]}}
逐行说明:
1) 校验 case_ids
2) 生成 run_id
3) 循环 execute_case
4) 返回 results
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/flows.py:get_flow_results', styles['SectionCN']))
story.append(Preformatted(f"""
输入: GET /api/flows/results/{fr_run_id}
输出示例(节选):
{{"flow_id": {fr_flow_id}, "run_id": "{fr_run_id}", "status": "{fr_status}", "steps": {json.dumps(flow_step_rows, ensure_ascii=False)} }}
逐行说明:
1) FlowRun 查询
2) FlowStepResult 查询
3) 组装返回
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/flows.py:list_flows', styles['SectionCN']))
story.append(Preformatted(f"""
输入:
GET /api/flows
输出示例:
[{{"id": {flow_id}, "name":"{flow_name}", "enabled": {flow_enabled}}}]
逐行说明:
1) query.all
2) 返回列表
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/flows.py:get_flow', styles['SectionCN']))
story.append(Preformatted(f"""
输入:
GET /api/flows/{flow_id}
输出示例:
{{"id": {flow_id}, "name":"{flow_name}", "steps": {json.dumps(flow_steps, ensure_ascii=False)} }}
逐行说明:
1) get_or_404
2) 返回对象
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/flows.py:create_flow', styles['SectionCN']))
story.append(Preformatted(f"""
输入:
POST /api/flows
{{"name":"{flow_name}", "steps": {json.dumps(flow_steps, ensure_ascii=False)} }}
输出示例:
{{"id": {flow_id}}}
逐行说明:
1) 校验 steps
2) add + commit
3) 返回 id
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/flows.py:update_flow', styles['SectionCN']))
story.append(Preformatted(f"""
输入:
PUT /api/flows/{flow_id}
{{"description":"updated"}}
输出示例:
{{"message":"updated"}}
逐行说明:
1) get_or_404
2) 校验 steps(如有)
3) commit
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/flows.py:delete_flow', styles['SectionCN']))
story.append(Preformatted(f"""
输入:
DELETE /api/flows/{flow_id}
输出示例:
{{"message":"deleted"}}
逐行说明:
1) get_or_404
2) delete + commit
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/flows.py:run_flow', styles['SectionCN']))
story.append(Preformatted(f"""
输入:
POST /api/flows/{flow_id}/run
{{"host":"172.17.12.101:9500"}}
输出示例:
{{"flow_id": {flow_id}, "run_id":"{fr_run_id}", "status":"{fr_status}"}}
逐行说明:
1) 读取 host
2) execute_flow
3) 返回结果
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/functions.py:list_functions', styles['SectionCN']))
story.append(Preformatted("""
输入:
GET /api/functions/
输出示例:
[{"name":"randomVer","parameters":[],"example":"randomVer()"}]
逐行说明:
1) get_registered_functions
2) 返回列表
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/functions.py:get_function_detail', styles['SectionCN']))
story.append(Preformatted("""
输入:
GET /api/functions/randomVer
输出示例:
{"name":"randomVer","parameters":[],"example":"randomVer()"}
逐行说明:
1) 查注册表
2) 返回详情
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/functions.py:execute_function_api', styles['SectionCN']))
story.append(Preformatted(f"""
输入:
POST /api/functions/execute
{{"name":"getFoStrategy","args":{{"num":2}}}}
输出示例:
{{"success": true, "result": "{','.join(fo_list[:2])}"}}
逐行说明:
1) 读取 name/args
2) execute_function
3) 返回结果
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/context.py:resolve', styles['SectionCN']))
story.append(Preformatted("""
输入: "Authorization: Bearer ${token}" (context.token = 'abc')
输出: "Authorization: Bearer 'abc'"
逐行说明:
1) regex 匹配 ${token}
2) get_by_path
3) repr(value) 替换
4) 返回字符串
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/context.py:get_by_path', styles['SectionCN']))
story.append(Preformatted("""
输入:
context={"steps":{"login":{"token":"abc"}}}, path="steps.login.token"
输出:
"abc"
逐行说明:
1) '.' 拆分路径
2) 逐级取值
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/context.py:set_by_path', styles['SectionCN']))
story.append(Preformatted("""
输入:
context={}, path="steps.login.token", value="abc"
输出:
context={"steps":{"login":{"token":"abc"}}}
逐行说明:
1) 逐级创建 dict
2) 设置最终值
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/extractor.py:extract', styles['SectionCN']))
story.append(Preformatted("""
输入:
response_json = {"data": {"token": "t-001"}}
extract_rules = {"token": "$.data.token"}
输出:
{"token": "t-001"}
逐行说明:
1) jsonpath_expr.find
2) 取首个匹配值
3) 返回结果
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/assertion.py:assert_one (path/function/jsonpath)', styles['SectionCN']))
story.append(Preformatted("""
输入(path): assertion={"type":"path","path":"data.id","operator":"eq","value":100}
实际: {"data": {"id": 100}}
输出: (True, "")

输入(jsonpath): assertion={"type":"jsonpath","jsonpath":"$.data.items[*].id","operator":"contains","value":3}
实际: {"data": {"items": [{"id":3}]}}
输出: (True, "")
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/parser.py:_validate_steps_list', styles['SectionCN']))
story.append(Preformatted("""
输入:
steps=[{"type":"step","name":"s1","api_id":1,"params":{}}]
输出:
同输入 steps
逐行说明:
1) 校验 list
2) validate_step(s1)
3) 返回
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/executor.py:_execute_steps (loop 示例)', styles['SectionCN']))
story.append(Preformatted(f"""
输入 steps(loop):
{json.dumps(step_loop, ensure_ascii=False, indent=2)}
输出: List[step result] (长度=3)
示例输出(节选):
[{{"step":"retry","status":"success"}}, ...]
逐行说明:
1) 解析 times=3
2) 循环执行 steps
3) 汇总结果
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/executor.py:_safe_eval', styles['SectionCN']))
story.append(Preformatted("""
输入:
expr="10 % 3 == 1"
输出:
True
逐行说明:
1) ast.parse
2) 检查节点安全
3) eval
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/executor.py:_eval_condition', styles['SectionCN']))
story.append(Preformatted("""
输入:
cond="${a} > 1" (context.a=2)
输出:
True
逐行说明:
1) resolve -> "2 > 1"
2) _safe_eval
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/executor.py:_resolve_step_from_case', styles['SectionCN']))
story.append(Preformatted(f"""
输入:
step={{"case_id": {case_id}}}
输出:
merged step (含 api_id={case_api_id}, params/assersions/extract)
逐行说明:
1) 查询 TestCase
2) 合并字段
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/executor.py:_execute_http_step', styles['SectionCN']))
story.append(Preformatted(f"""
输入:
step={{"name":"s1","api_id": {api_id}, "params": {json.dumps(case_params, ensure_ascii=False)} }}
输出:
{{"step":"s1","status":"success|fail","http_status":200,...}}
逐行说明:
1) resolve_params
2) 请求接口
3) 断言/提取
4) 返回结果
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/executor.py:execute_flow', styles['SectionCN']))
story.append(Preformatted(f"""
输入:
execute_flow({flow_id}, host="172.17.12.101:9500")
输出:
{{"flow_id": {flow_id}, "run_id":"{fr_run_id}", "results":[...]}}
逐行说明:
1) 创建 FlowRun
2) 执行 steps
3) 写入 FlowStepResult
4) 更新 FlowRun
""".strip(), styles['CodeCN']))

# Build

doc.build(story)
print(f'generated {pdf_path}')
