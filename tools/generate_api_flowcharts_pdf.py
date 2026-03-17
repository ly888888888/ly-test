# -*- coding: utf-8 -*-
from datetime import datetime
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
    # Fallback to SimHei if available
    font_path = r"C:\\Windows\\Fonts\\simhei.ttf"
    pdfmetrics.registerFont(TTFont('SimHei', font_path))
    base_font = 'SimHei'

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyCN', fontName=base_font, fontSize=10, leading=14, spaceAfter=6))
styles.add(ParagraphStyle(name='TitleCN', fontName=base_font, fontSize=16, leading=20, spaceAfter=12))
styles.add(ParagraphStyle(name='SectionCN', fontName=base_font, fontSize=12, leading=16, spaceAfter=8))
styles.add(ParagraphStyle(name='CodeCN', fontName=base_font, fontSize=9, leading=12))

now = datetime.now().strftime('%Y-%m-%d %H:%M')

doc = SimpleDocTemplate(
    'api_flowcharts_multi_v4.pdf',
    pagesize=A4,
    leftMargin=18*mm,
    rightMargin=18*mm,
    topMargin=15*mm,
    bottomMargin=15*mm
)

story = []
story.append(Paragraph('项目接口流程图与说明', styles['TitleCN']))
story.append(Paragraph(f'生成时间: {now}', styles['BodyCN']))
story.append(Paragraph('范围: C:\\D\\ly_test_platform (Flask + SQLAlchemy)', styles['BodyCN']))
story.append(Spacer(1, 6))


def add_section(title, method, handler, purpose, flow_ascii, example_req, example_resp, steps, io_fields):
    story.append(Paragraph(title, styles['SectionCN']))
    story.append(Paragraph(f'接口方法: {method}', styles['BodyCN']))
    story.append(Paragraph(f'处理函数: {handler}', styles['BodyCN']))
    story.append(Paragraph(f'作用: {purpose}', styles['BodyCN']))
    story.append(Paragraph('输入/输出字段:', styles['BodyCN']))
    story.append(Preformatted(io_fields, styles['CodeCN']))
    story.append(Paragraph('流程图(ASCII):', styles['BodyCN']))
    story.append(Preformatted(flow_ascii, styles['CodeCN']))
    story.append(Paragraph('示例请求:', styles['BodyCN']))
    story.append(Preformatted(example_req, styles['CodeCN']))
    story.append(Paragraph('示例响应:', styles['BodyCN']))
    story.append(Preformatted(example_resp, styles['CodeCN']))
    story.append(Paragraph('实现步骤:', styles['BodyCN']))
    story.append(Preformatted(steps, styles['CodeCN']))
    story.append(Spacer(1, 8))


# 1) GET /api/interfaces
add_section(
    '1) GET /api/interfaces',
    'GET',
    'api/interfaces.py:list_interfaces',
    '查询接口定义列表, 支持 project/path/method 过滤, 返回 ApiDefinition 列表',
    """
[Client]
  |
  v
[Flask Blueprint /api/interfaces]
  |
  v
[list_interfaces()]
  |
  v
[SQLAlchemy ApiDefinition.query + filters]
  |
  v
[DB: api_definition]
  |
  v
[JSON list response]
""".strip(),
    """GET /api/interfaces?project=demo&path=/user&method=GET""",
    """[
  {"id": 1, "project": "demo", "path": "/user", "method": "GET", "schema": {...}, "description": "list users"}
]""",
    """1. 从 query string 读取 project/path/method
2. 逐步追加 filter_by 条件
3. query.all() 拉取接口列表
4. 组装 JSON 列表并返回
""".strip(),
    """Input:
- project (query, optional)
- path (query, optional)
- method (query, optional)
Output:
- list[ {id, project, path, method, schema, description} ]
""".strip()
)

# 3) GET /api/interfaces/{id}
add_section(
    '3) GET /api/interfaces/{id}',
    'GET',
    'api/interfaces.py:get_interface',
    '按 id 获取接口定义详情',
    """
[Client]
  |
  v
[Flask Blueprint /api/interfaces/<id>]
  |
  v
[get_interface(id)]
  |
  v
[ApiDefinition.query.get_or_404]
  |
  v
[DB: api_definition]
  |
  v
[JSON object response]
""".strip(),
    """GET /api/interfaces/1""",
    """{"id": 1, "project": "demo", "path": "/user", "method": "GET", "schema": {...}, "description": "list users"}""",
    """1. 解析 path 参数 id
2. get_or_404 查询记录
3. 组装 JSON 对象返回
""".strip(),
    """Input:
- id (path, required)
Output:
- {id, project, path, method, schema, description}
""".strip()
)

# Multi-interface flow coverage
story.append(Paragraph('多接口流程概览', styles['SectionCN']))
story.append(Preformatted("""
接口管理:
- POST /api/interfaces        创建接口定义
- GET  /api/interfaces        查询接口定义列表
- GET  /api/interfaces/{id}   获取单个接口定义
- PUT  /api/interfaces/{id}   更新接口定义
- DELETE /api/interfaces/{id} 删除接口定义(被用例引用则拒绝)

测试用例:
- POST /api/testcases          创建测试用例(校验 api_id)
- GET  /api/testcases          查询测试用例列表
- GET  /api/testcases/{id}     获取单个用例
- PUT  /api/testcases/{id}     更新测试用例
- DELETE /api/testcases/{id}   删除测试用例

执行与结果:
- POST /api/run/testcase/{id}  单用例执行
- POST /api/run/suite          批量执行
- GET  /api/run/results/{rid}  查询执行结果

流程编排:
- POST /api/flows              创建流程(校验 DSL)
- GET  /api/flows              查询流程列表
- GET  /api/flows/{id}         获取流程
- PUT  /api/flows/{id}         更新流程
- DELETE /api/flows/{id}       删除流程
- POST /api/flows/{id}/run     执行流程
- GET  /api/flows/results/{rid} 查询流程结果

自定义函数:
- GET  /api/functions/         查询可用函数列表
- GET  /api/functions/{name}   查询函数详情
- POST /api/functions/execute  执行函数
""".strip(), styles['CodeCN']))

story.append(Paragraph('多接口联动示例流程', styles['SectionCN']))
story.append(Paragraph('示例目标: 创建接口 -> 创建用例 -> 执行用例 -> 查询结果', styles['BodyCN']))
story.append(Preformatted("""
1) POST /api/interfaces
请求:
{
  "project": "demo",
  "path": "/user/profile",
  "method": "POST",
  "schema": {"type": "object"},
  "description": "user profile"
}
响应: {"id": 12}

2) POST /api/testcases
请求:
{
  "project": "demo",
  "name": "get_profile_logic",
  "api_id": 12,
  "test_type": "logic",
  "params": {
    "uid": {"type": "fixed", "value": 10001},
    "version": {"type": "function", "function": "randomVer", "args": {}},
    "strategy_id": {"type": "function", "function": "getFoStrategy", "args": {"num": 2}},
    "scene": {"type": "db_query", "sql": "SELECT scene FROM config_scene LIMIT 1"}
  },
  "assertions": [
    {"type": "path", "path": "data.user.id", "operator": "eq", "value": "${uid}"},
    {"type": "function", "function": "check_tabs", "args": {"brand": "funshion", "version": "${version}"}},
    {"type": "jsonpath", "jsonpath": "$.data.tabs[*].name", "operator": "contains", "value": "首页"}
  ],
  "extract": {"token": "$.data.token"}
}
响应: {"id": 100}

3) POST /api/run/testcase/100
请求: {"host": "127.0.0.1:5000"}
响应: {"case_id": 100, "status": "success", "run_id": "r-001"}

4) GET /api/run/results/r-001
响应: [{"case_id": 100, "status": "success", "http_status": 200, "duration_ms": 120}]
""".strip(), styles['CodeCN']))

# Extra: DSL engine + detailed example
story.append(Paragraph('DSL 引擎实现要点', styles['SectionCN']))
story.append(Paragraph('覆盖变量系统、响应提取、断言增强、流程执行（含条件/循环）、数据驱动。', styles['BodyCN']))
story.append(Preformatted("""
1) 变量系统 (dsl/context.py)
- Context.set_by_path / get_by_path 管理上下文变量
- ${变量路径} 语法在 resolve 中替换
- 示例: ${steps.login.token} / ${data.user_id}

2) 响应提取 (dsl/extractor.py)
- JSONPath 提取: {"token": "$.data.token"}
- 提取结果写入 Context: steps.<step_name>.<var>

3) 断言增强 (dsl/assertion.py)
- path 断言: data.user.id eq 10001
- function 断言: 通过注册函数检查复杂逻辑
- jsonpath 断言: $.data.items[*].id contains 3

4) 流程执行 (dsl/executor.py)
- 支持 step / condition / loop
- 条件: if/then/else + safe_eval
- 循环: times + steps

5) 数据驱动 (dsl/executor.py)
- flow.data_source 为多行数据
- 每行数据生成一个 iteration，上下文路径 data.<field>
""".strip(), styles['CodeCN']))

story.append(Paragraph('重点示例: 逻辑测试用例(含多类型参数与断言)', styles['SectionCN']))
story.append(Paragraph('示例目标: 请求 /user/profile ，校验用户信息并提取 token', styles['BodyCN']))

story.append(Preformatted("""
测试用例 (TestCase)
{
  "project": "demo",
  "name": "get_profile_logic",
  "api_id": 12,
  "test_type": "logic",
  "expected_status": 200,
  "params": {
    "uid": {"type": "fixed", "value": 10001},
    "version": {"type": "function", "function": "randomVer", "args": {}},
    "strategy_id": {"type": "function", "function": "getFoStrategy", "args": {"num": 2}},
    "scene": {"type": "db_query", "sql": "SELECT scene FROM config_scene LIMIT 1"}
  },
  "assertions": [
    {"type": "path", "path": "data.user.id", "operator": "eq", "value": "${uid}"},
    {"type": "function", "function": "check_tabs", "args": {"brand": "funshion", "version": "${version}"}},
    {"type": "jsonpath", "jsonpath": "$.data.tabs[*].name", "operator": "contains", "value": "首页"}
  ],
  "extract": {"token": "$.data.token"}
}
""".strip(), styles['CodeCN']))

story.append(Paragraph('实例参数解析与每步结果(示例输出)', styles['BodyCN']))
story.append(Preformatted("""
Step 1: resolve_params
- fixed uid = 10001
- function randomVer() -> "5.3.8.4"
- function getFoStrategy(num=2) -> "101,205"
- db_query -> "scene_home" (示例结果)
输出 params:
{
  "uid": 10001,
  "version": "5.3.8.4",
  "strategy_id": "101,205",
  "scene": "scene_home"
}

Step 2: resolve_variables (无 ${} 时保持不变)
输出 params 同上

Step 3: HttpClient 请求
POST http://<host>/user/profile
Body = params
响应示例:
{
  "data": {
    "token": "t-abc-001",
    "user": {"id": 10001, "name": "Alice"},
    "tabs": [{"name": "首页"}, {"name": "搜索"}]
  }
}

Step 4: 断言执行
- path: data.user.id eq ${uid} -> 10001 == 10001 -> OK
- function: check_tabs(brand=funshion, version=5.3.8.4) -> (True, "")
- jsonpath: $.data.tabs[*].name contains "首页" -> OK
断言结果: 全部通过

Step 5: 提取变量
- token = $.data.token -> "t-abc-001"
写入 Context: steps.get_profile_logic.token = "t-abc-001"

Step 6: 写入 TestResult
status=success, http_status=200, error_info=""
""".strip(), styles['CodeCN']))

story.append(Paragraph('补充: /api/run/testcase/{case_id} 分支流程 (test_type)', styles['SectionCN']))
story.append(Paragraph('目的: 展开 execute_case 内部不同 test_type 的流程', styles['BodyCN']))
story.append(Preformatted("""
[execute_case]
  |
  +--> smoke: HttpClient 请求 -> 校验 HTTP 状态 -> 记录 TestResult
  |
  +--> structural: jsonschema 校验 -> 记录 TestResult
  |
  +--> logic/monitor: HttpClient 请求 -> AssertionEngine 断言 -> Extractor 提取 -> 记录 TestResult
  |
  +--> compare: compare_test_common 对比新旧 host -> 记录 TestResult
  |
  +--> other: 返回 Unsupported test type
""".strip(), styles['CodeCN']))

story.append(Paragraph('分支示例: test_type=logic (步骤同上)', styles['BodyCN']))

story.append(Paragraph('多接口流程场景详解 (多步骤编排/变量传递/条件/循环/数据驱动)', styles['SectionCN']))
story.append(Paragraph('场景目标: 登录 -> 拉取配置 -> 条件判断 -> 循环查询推荐 -> 汇总结果', styles['BodyCN']))
story.append(Preformatted("""
流程定义 (TestFlow.steps):
[
  {
    "type": "step",
    "name": "login",
    "api_id": 1,
    "params": {
      "user": {"type": "fixed", "value": "${data.user}"},
      "password": {"type": "fixed", "value": "${data.password}"}
    },
    "extract": {"token": "$.data.token"},
    "assertions": [
      {"type": "path", "path": "status", "operator": "eq", "value": 200}
    ]
  },
  {
    "type": "step",
    "name": "get_config",
    "api_id": 2,
    "params": {
      "token": {"type": "fixed", "value": "${steps.login.token}"},
      "version": {"type": "function", "function": "randomVer", "args": {}}
    },
    "extract": {"is_vip": "$.data.vip"}
  },
  {
    "type": "condition",
    "name": "vip_gate",
    "if": "${steps.get_config.is_vip} == True",
    "then": [
      {
        "type": "step",
        "name": "vip_reco",
        "api_id": 3,
        "params": {"token": {"type": "fixed", "value": "${steps.login.token}"}}
      }
    ],
    "else": [
      {
        "type": "step",
        "name": "free_reco",
        "api_id": 4,
        "params": {"token": {"type": "fixed", "value": "${steps.login.token}"}}
      }
    ]
  },
  {
    "type": "loop",
    "name": "repeat_query",
    "times": 3,
    "steps": [
      {
        "type": "step",
        "name": "query_item",
        "api_id": 5,
        "params": {
          "token": {"type": "fixed", "value": "${steps.login.token}"},
          "scene": {"type": "db_query", "sql": "SELECT scene FROM config_scene LIMIT 1"}
        }
      }
    ]
  }
]
数据驱动 (data_source):
[
  {"user": "alice", "password": "p1"},
  {"user": "bob", "password": "p2"}
]
""".strip(), styles['CodeCN']))

story.append(Paragraph('场景执行过程与变量流转(示例输出)', styles['BodyCN']))
story.append(Preformatted("""
Iteration #0 (data.user=alice):
1) login
- 请求参数: user=alice, password=p1
- 响应: {"data": {"token": "t-alice"}}
- 提取: steps.login.token = "t-alice"

2) get_config
- params: token=${steps.login.token} -> "t-alice"
- 响应: {"data": {"vip": true}}
- 提取: steps.get_config.is_vip = true

3) vip_gate (condition)
- 条件: true -> 走 then 分支
- 执行 vip_reco(api_id=3), token="t-alice"

4) repeat_query (loop x3)
- 每次 query_item 使用相同 token, scene 来自 db_query
- 记录 3 次结果

Iteration #1 (data.user=bob):
... 同样流程, 使用 bob 的参数与 token
""".strip(), styles['CodeCN']))

story.append(Paragraph('各 Python 文件的类/方法输入输出与示例', styles['SectionCN']))
story.append(Paragraph('覆盖主要模块: app, api, models, dsl, tools', styles['BodyCN']))

story.append(Paragraph('app.py', styles['SectionCN']))
story.append(Preformatted("""
create_app() -> Flask app
输入: 无
输出: Flask 应用实例
示例:
app = create_app()
""".strip(), styles['CodeCN']))

# Real DB/response examples (from test_platform and db_jupiter_operation)
story.append(Paragraph('真实数据库/接口示例数据 (已从现有数据库读取)', styles['SectionCN']))
story.append(Preformatted("""
数据库: test_platform
api_definition:
- id=1, project=edubox, path=/edu/funclock/homepage/english, method=GET, description=英语首页接口

test_case:
- id=1, project=edubox, name=英语首页 逻辑测试, api_id=1, test_type=logic
- params={"isencode":{"type":"fixed","value":1}}
- assertions=[{"path":"data[1000]","type":"path","value":null,"operator":"ne"}]
- extract=null, expected_status=200

test_flow:
- id=1, name=英语首页流程, enabled=1
- steps=[{"name":"step1","api_id":1,"params":{"isencode":{"type":"fixed","value":1}},
          "assertions":[{"path":"data[0].action_template","type":"path","value":"sync_lesson","operator":"eq"}]}]

test_result (真实响应片段):
- case_id=1, http_status=200, response_body={"retCode":"-1","retMsg":"404","data":[]}

数据库: db_jupiter_operation
fo_strategy:
- strategy_id 示例: 2, 3, 4, 8, 9
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/ 文件逐行级说明与示例', styles['SectionCN']))
story.append(Paragraph('以下为 api 目录每个方法的逐行级说明 + 输入/输出 + 示例', styles['BodyCN']))

story.append(Paragraph('api/interfaces.py:list_interfaces', styles['SectionCN']))
story.append(Preformatted("""
输入: request.args(project?, path?, method?)
输出: JSON list
逐行说明:
1. 读取 query 参数 project/path/method
2. 创建 ApiDefinition.query
3. 如果 project 存在 -> filter_by(project=...)
4. 如果 path 存在 -> filter_by(path=...)
5. 如果 method 存在 -> filter_by(method=...)
6. query.all() 拉取数据
7. 组装列表 [{id,project,path,method,schema,description}]
8. jsonify 返回
示例:
GET /api/interfaces?project=edubox -> 返回 api_definition 列表
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/interfaces.py:create_interface', styles['SectionCN']))
story.append(Preformatted("""
输入: JSON {project,path,method,schema,description?}
输出: {"id": int} 或 400
逐行说明:
1. request.get_json() 获取 body
2. 校验必填字段 project/path/method/schema
3. 缺失 -> 返回 400
4. 创建 ApiDefinition 实例
5. db.session.add
6. db.session.commit
7. 返回 {"id": interface.id}
示例:
POST /api/interfaces {project:"edubox", path:"/edu/...", method:"GET", schema:{...}}
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/interfaces.py:get_interface', styles['SectionCN']))
story.append(Preformatted("""
输入: path id
输出: JSON object
逐行说明:
1. ApiDefinition.query.get_or_404(id)
2. 组装字段 JSON
3. jsonify 返回
示例:
GET /api/interfaces/1 -> 返回英语首页接口定义
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/interfaces.py:update_interface', styles['SectionCN']))
story.append(Preformatted("""
输入: path id + JSON
输出: {"message":"updated"}
逐行说明:
1. get_or_404(id)
2. 读取 JSON body
3. 遍历允许字段 project/path/method/schema/description
4. field 存在则 setattr
5. db.session.commit
6. 返回 updated
示例:
PUT /api/interfaces/1 {"description":"英语首页接口 v2"}
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/interfaces.py:delete_interface', styles['SectionCN']))
story.append(Preformatted("""
输入: path id
输出: {"message":"deleted"} 或 400
逐行说明:
1. get_or_404(id)
2. 检查 interface.test_cases 是否非空
3. 若有用例引用 -> 400
4. 删除记录并提交
5. 返回 deleted
示例:
DELETE /api/interfaces/1
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/testcases.py:create_testcase', styles['SectionCN']))
story.append(Preformatted("""
输入: JSON {project,name,api_id,test_type,params,...}
输出: {"id": int} 或 404/400
逐行说明:
1. request.get_json()
2. 校验必填字段
3. ApiDefinition.query.get(api_id)
4. 不存在 -> 404
5. 构造 TestCase
6. db.session.add + commit
7. 返回 id
真实示例:
test_case id=1 (英语首页 逻辑测试)
params={"isencode":{"type":"fixed","value":1}}
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/run.py:execute_case', styles['SectionCN']))
story.append(Preformatted("""
输入: case_id, host, run_id?, host_compare?
输出: 执行结果 dict
逐行说明(核心路径):
1. 若 run_id 为空 -> uuid
2. 查询 TestCase -> 不存在/disabled 返回 error
3. 取 api/method/context
4. resolve_params -> resolve_variables
5. 构造 URL/body
6. 根据 test_type 分支执行请求/校验/对比
7. 计算耗时
8. 记录 TestResult
9. 返回摘要结果
真实响应示例:
case_id=1 -> response_body={"retCode":"-1","retMsg":"404","data":[]}
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/ 文件逐行级说明与示例', styles['SectionCN']))
story.append(Paragraph('以下为 dsl 目录每个方法逐行级说明 + 输入/输出 + 示例', styles['BodyCN']))

story.append(Paragraph('dsl/context.py:Context.resolve', styles['SectionCN']))
story.append(Preformatted("""
输入: text (含 ${变量路径})
输出: 替换后的字符串
逐行说明:
1. 正则匹配 ${...}
2. get_by_path 查上下文
3. None -> 抛异常
4. 使用 repr(value) 替换
5. 返回替换后的文本
示例:
Context({"token":"abc"}).resolve("Bearer ${token}") -> "Bearer 'abc'"
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/testcases.py:list_testcases', styles['SectionCN']))
story.append(Preformatted("""
输入: query(project?, api_id?, test_type?)
输出: JSON list
逐行说明:
1. 读取 query 参数
2. TestCase.query 初始化
3. 按条件 filter_by
4. query.all()
5. 组装列表返回
示例:
GET /api/testcases?project=edubox
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/testcases.py:get_testcase', styles['SectionCN']))
story.append(Preformatted("""
输入: path id
输出: JSON object
逐行说明:
1. TestCase.query.get_or_404(id)
2. 组装字段
3. jsonify 返回
示例:
GET /api/testcases/1 -> 英语首页 逻辑测试
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/testcases.py:update_testcase', styles['SectionCN']))
story.append(Preformatted("""
输入: path id + JSON
输出: {"message":"updated"}
逐行说明:
1. get_or_404(id)
2. 读取 JSON
3. 遍历允许字段并 setattr
4. commit
5. 返回 updated
示例:
PUT /api/testcases/1 {"enabled": false}
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/testcases.py:delete_testcase', styles['SectionCN']))
story.append(Preformatted("""
输入: path id
输出: {"message":"deleted"}
逐行说明:
1. get_or_404(id)
2. db.session.delete
3. commit
4. 返回 deleted
示例:
DELETE /api/testcases/1
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/run.py:run_single', styles['SectionCN']))
story.append(Preformatted("""
输入: JSON {host?, host_compare?}
输出: 执行结果 + run_id
逐行说明:
1. 读取 body (为空则 {})
2. host 默认 DEFAULT_HOST
3. 生成 run_id
4. 调用 execute_case
5. 补充 run_id 返回
示例:
POST /api/run/testcase/1 {"host":"172.17.12.101:9500"}
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/run.py:run_suite', styles['SectionCN']))
story.append(Preformatted("""
输入: JSON {case_ids, host?, host_compare?, loop_times?}
输出: {run_id, results}
逐行说明:
1. 校验 case_ids
2. 读取 host/host_compare/loop_times
3. 生成 run_id
4. 双层循环执行 execute_case
5. 汇总 results 返回
示例:
POST /api/run/suite {"case_ids":[1], "loop_times":2}
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/run.py:get_results', styles['SectionCN']))
story.append(Preformatted("""
输入: run_id
输出: List[TestResult]
逐行说明:
1. filter_by(run_id)
2. all()
3. 组装列表返回
示例:
GET /api/run/results/1cccb93e-...
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/functions.py:list_functions', styles['SectionCN']))
story.append(Preformatted("""
输入: 无
输出: 自定义函数元信息列表
逐行说明:
1. custom_functions.get_registered_functions()
2. jsonify 返回
示例:
GET /api/functions/
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/functions.py:get_function_detail', styles['SectionCN']))
story.append(Preformatted("""
输入: path name
输出: 单个函数元信息或 404
逐行说明:
1. 从 _FUNCTION_REGISTRY 取信息
2. 不存在 -> 404
3. 返回 name/description/parameters/example
示例:
GET /api/functions/randomVer
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/functions.py:execute_function_api', styles['SectionCN']))
story.append(Preformatted("""
输入: JSON {name, args}
输出: {success, result} 或 400
逐行说明:
1. 读取 name/args
2. custom_functions.execute_function
3. 成功返回 result
4. 异常返回 error
示例:
POST /api/functions/execute {"name":"randomVer","args":{}}
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/flows.py:list_flows', styles['SectionCN']))
story.append(Preformatted("""
输入: 无
输出: List[TestFlow]
逐行说明:
1. TestFlow.query.all
2. 组装 JSON 列表
3. 返回
示例:
GET /api/flows -> 返回流程列表
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/flows.py:get_flow', styles['SectionCN']))
story.append(Preformatted("""
输入: flow_id
输出: TestFlow
逐行说明:
1. get_or_404(flow_id)
2. 组装 JSON
3. 返回
示例:
GET /api/flows/1 -> 英语首页流程
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/flows.py:create_flow', styles['SectionCN']))
story.append(Preformatted("""
输入: JSON {name, steps, data_source?, enabled?}
输出: {"id": int} 或 400
逐行说明:
1. 读取 body
2. 校验 name/steps
3. validate_flow_steps
4. 保存 TestFlow
5. 返回 id
示例:
POST /api/flows {"name":"英语首页流程","steps":[...]}
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/flows.py:update_flow', styles['SectionCN']))
story.append(Preformatted("""
输入: flow_id + JSON
输出: {"message":"updated"} 或 400
逐行说明:
1. get_or_404
2. 若 steps 存在 -> validate_flow_steps
3. 更新字段
4. commit
5. 返回 updated
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/flows.py:delete_flow', styles['SectionCN']))
story.append(Preformatted("""
输入: flow_id
输出: {"message":"deleted"}
逐行说明:
1. get_or_404
2. delete + commit
3. 返回 deleted
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/flows.py:run_flow', styles['SectionCN']))
story.append(Preformatted("""
输入: flow_id + JSON {host?, host_compare?}
输出: {flow_id, run_id, results}
逐行说明:
1. 读取 host/host_compare
2. execute_flow(flow_id,...)
3. 返回结果
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/flows.py:get_flow_results', styles['SectionCN']))
story.append(Preformatted("""
输入: run_id
输出: flow 执行详情或 404
逐行说明:
1. FlowRun.query.filter_by(run_id).first()
2. 不存在 -> 404
3. FlowStepResult.query.filter_by(flow_run_id)
4. 组装 JSON 返回
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/custom_functions.py', styles['SectionCN']))
story.append(Preformatted("""
register(func) -> func
输入: function
输出: 注册后的 function
逐行说明:
1. inspect.signature 取参数
2. 生成 example 字符串
3. 写入 _FUNCTION_REGISTRY
4. 返回 func

get_registered_functions() -> list
输入: 无
输出: [{name,description,parameters,example}]

get_function(name) -> func|None
输入: name
输出: function 或 None

execute_function(name, **kwargs) -> result
输入: name/args
输出: function 结果 或异常

getFoStrategy(num) -> "id1,id2"
输入: num(int)
输出: 逗号分隔策略ID
真实示例: num=2 -> "2,3"

randomVer() -> str
输入: 无
输出: 版本号随机值

check_tabs(response_json, brand, version) -> (bool, msg)
输入: response_json + brand/version
输出: 断言结果与消息
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/utils.py:resolve_params', styles['SectionCN']))
story.append(Preformatted("""
输入: params_def(JSON)
输出: 解析后的 dict
逐行说明:
1. 遍历 params_def
2. fixed -> 取 value
3. db_query -> 执行 SQL
4. function -> 调用 custom_functions
5. random -> 返回随机值占位
6. 返回 resolved
示例:
{"isencode":{"type":"fixed","value":1}} -> {"isencode":1}
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/utils.py:get_value_by_path', styles['SectionCN']))
story.append(Preformatted("""
输入: obj + path
输出: value 或 None
逐行说明:
1. path 按 '.' 拆分
2. 支持 data[0] / data.0
3. 逐级访问 dict/list
4. 越界/类型不匹配 -> None
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/utils.py:resolve_variables', styles['SectionCN']))
story.append(Preformatted("""
输入: value(含 ${} 变量)
输出: 替换后的 value
逐行说明:
1. str -> context.resolve
2. dict -> 递归处理
3. list -> 递归处理
4. 其他类型原样返回
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/utils.py:compare_value', styles['SectionCN']))
story.append(Preformatted("""
输入: actual, operator, expected
输出: bool
逐行说明:
1. 根据 operator 选择比较方式
2. 返回比较结果
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/context.py:get_by_path', styles['SectionCN']))
story.append(Preformatted("""
输入: path
输出: value 或 None
逐行说明:
1. path '.' 拆分
2. 逐级从 dict 取值
3. 非 dict -> None
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/context.py:set_by_path', styles['SectionCN']))
story.append(Preformatted("""
输入: path, value
输出: None
逐行说明:
1. 拆分 path
2. 逐级创建中间 dict
3. 设置最后节点
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/extractor.py:Extractor.extract', styles['SectionCN']))
story.append(Preformatted("""
输入: response_json, extract_rules
输出: dict
逐行说明:
1. 遍历规则
2. jsonpath_expr.find()
3. 命中取第一个值
4. 未命中 -> None
5. 返回结果
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/assertion.py:AssertionEngine.assert_one', styles['SectionCN']))
story.append(Preformatted("""
输入: assertion, actual_value, context
输出: (ok, msg)
逐行说明:
1. 读取 assertion.type
2. path: get_value_by_path + compare_value
3. function: 解析 args -> 调用注册函数
4. jsonpath: 提取并比较
5. 返回结果
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/parser.py:_validate_steps_list', styles['SectionCN']))
story.append(Preformatted("""
输入: steps(list)
输出: steps(list) 或异常
逐行说明:
1. 校验为 list
2. 逐个 validate_step
3. 返回
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/parser.py:validate_step', styles['SectionCN']))
story.append(Preformatted("""
输入: step(dict)
输出: step 或异常
逐行说明:
1. 读取 step.type (默认 step)
2. step: 校验 name/api_id/params 或 case_id 规则
3. condition: 校验 if + then/else
4. loop: 校验 times/steps
5. 其他 type -> 异常
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/parser.py:validate_flow_steps', styles['SectionCN']))
story.append(Preformatted("""
输入: steps
输出: steps
逐行说明:
1. 调用 _validate_steps_list
2. 返回结果
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/executor.py:_safe_eval', styles['SectionCN']))
story.append(Preformatted("""
输入: expr
输出: bool/值 或异常
逐行说明:
1. ast.parse
2. 遍历节点，限制安全类型
3. 编译并 eval
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/executor.py:_eval_condition', styles['SectionCN']))
story.append(Preformatted("""
输入: cond, context
输出: bool
逐行说明:
1. 字符串 -> context.resolve
2. 解析结果若为 str -> _safe_eval
3. 其他类型 -> bool()
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/executor.py:_resolve_step_from_case', styles['SectionCN']))
story.append(Preformatted("""
输入: step (含 case_id)
输出: (merged_step, err)
逐行说明:
1. 查询 TestCase
2. 不存在/disabled -> error
3. 合并 case 与 step 覆盖字段
4. 返回 merged
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/executor.py:_execute_http_step', styles['SectionCN']))
story.append(Preformatted("""
输入: step, host, context
输出: step result dict
逐行说明:
1. case_id -> _resolve_step_from_case
2. 查询 ApiDefinition
3. resolve_params + resolve_variables
4. 构造 URL/body
5. HttpClient 发送请求
6. 断言 + 提取
7. 返回结果 dict
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/executor.py:execute_flow', styles['SectionCN']))
story.append(Preformatted("""
输入: flow_id, host, host_compare?
输出: {flow_id, run_id, results}
逐行说明:
1. 查询 TestFlow
2. 创建 FlowRun
3. 若 data_source -> 多 iteration
4. 调用 _execute_steps
5. 写入 FlowStepResult
6. 更新 FlowRun 状态与耗时
7. 返回结果
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/executor.py:_execute_steps', styles['SectionCN']))
story.append(Preformatted("""
输入: steps, host, context, depth, max_depth, iteration_index
输出: List[step result]
逐行说明:
1. 深度超限 -> 返回 error step
2. 遍历 steps
3. step -> _execute_http_step
4. condition -> _eval_condition -> then/else 递归
5. loop -> 解析 times -> 递归执行 steps
6. 其他 type -> error
7. 汇总结果返回
示例:
steps=[{type:step},{type:condition},{type:loop}]
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/interfaces.py', styles['SectionCN']))
story.append(Preformatted("""
list_interfaces() [GET /api/interfaces]
输入: query(project, path, method)
输出: List[ApiDefinition]
示例: GET /api/interfaces?project=demo

create_interface() [POST /api/interfaces]
输入: JSON {project,path,method,schema,description?}
输出: {"id": int}
示例: POST /api/interfaces {...}

get_interface(id) [GET /api/interfaces/{id}]
输入: path id
输出: ApiDefinition 对象
示例: GET /api/interfaces/1

update_interface(id) [PUT /api/interfaces/{id}]
输入: path id + JSON(可选字段)
输出: {"message":"updated"}
示例: PUT /api/interfaces/1 {"description":"..."}

delete_interface(id) [DELETE /api/interfaces/{id}]
输入: path id
输出: {"message":"deleted"} 或 400
示例: DELETE /api/interfaces/1
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/testcases.py', styles['SectionCN']))
story.append(Preformatted("""
list_testcases() [GET /api/testcases]
输入: query(project, api_id, test_type)
输出: List[TestCase]
示例: GET /api/testcases?test_type=logic

create_testcase() [POST /api/testcases]
输入: JSON {project,name,api_id,test_type,params,...}
输出: {"id": int}
示例: POST /api/testcases {...}

get_testcase(id) [GET /api/testcases/{id}]
输入: path id
输出: TestCase 对象

update_testcase(id) [PUT /api/testcases/{id}]
输入: path id + JSON
输出: {"message":"updated"}

delete_testcase(id) [DELETE /api/testcases/{id}]
输入: path id
输出: {"message":"deleted"}
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/run.py', styles['SectionCN']))
story.append(Preformatted("""
execute_case(case_id, host, run_id=None, host_compare=None) -> dict
输入: case_id(int), host(str), run_id(str?), host_compare(str?)
输出: {case_id,status,http_status,error_info,duration_ms}
示例: execute_case(10, "127.0.0.1:5000")

run_single(case_id) [POST /api/run/testcase/{case_id}]
输入: JSON {host?, host_compare?}
输出: 执行结果 + run_id

run_suite() [POST /api/run/suite]
输入: JSON {case_ids, host?, host_compare?, loop_times?}
输出: {run_id, results}

get_results(run_id) [GET /api/run/results/{run_id}]
输入: run_id
输出: List[TestResult]
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/functions.py', styles['SectionCN']))
story.append(Preformatted("""
list_functions() [GET /api/functions/]
输入: 无
输出: List[function meta]

get_function_detail(name) [GET /api/functions/{name}]
输入: name
输出: {name, description, parameters, example}

execute_function_api() [POST /api/functions/execute]
输入: JSON {name, args}
输出: {success, result | error}
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/flows.py', styles['SectionCN']))
story.append(Preformatted("""
list_flows() [GET /api/flows]
输入: 无
输出: List[TestFlow]

get_flow(flow_id) [GET /api/flows/{id}]
输入: flow_id
输出: TestFlow

create_flow() [POST /api/flows]
输入: JSON {name, steps, data_source?, enabled?}
输出: {"id": int}

update_flow(flow_id) [PUT /api/flows/{id}]
输入: flow_id + JSON
输出: {"message":"updated"}

delete_flow(flow_id) [DELETE /api/flows/{id}]
输入: flow_id
输出: {"message":"deleted"}

run_flow(flow_id) [POST /api/flows/{id}/run]
输入: JSON {host?, host_compare?}
输出: {flow_id, run_id, results}

get_flow_results(run_id) [GET /api/flows/results/{run_id}]
输入: run_id
输出: {flow_id, status, steps[]}
""".strip(), styles['CodeCN']))

story.append(Paragraph('models.py', styles['SectionCN']))
story.append(Preformatted("""
ApiDefinition: {id, project, path, method, schema, description}
TestCase: {id, project, name, api_id, test_type, params, assertions, extract, expected_status}
TestResult: {case_id, run_id, status, http_status, error_info, duration_ms}
TestFlow: {id, name, steps, data_source, enabled}
FlowRun: {flow_id, run_id, status, duration_ms}
FlowStepResult: {flow_run_id, step_name, step_type, status, extracted, duration_ms}
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/context.py', styles['SectionCN']))
story.append(Preformatted("""
Context.get_by_path(path) -> value
输入: "steps.login.token"
输出: value 或 None
示例: ctx.get_by_path("steps.login.token")

Context.set_by_path(path, value) -> None
输入: path, value
输出: None
示例: ctx.set_by_path("steps.login.token", "abc")

Context.resolve(text) -> str
输入: "Bearer ${token}"
输出: "Bearer abc"
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/extractor.py', styles['SectionCN']))
story.append(Preformatted("""
Extractor.extract(response_json, extract_rules) -> dict
输入: response_json, {"token": "$.data.token"}
输出: {"token": "..."}
示例: Extractor.extract(resp, {"token":"$.data.token"})
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/assertion.py', styles['SectionCN']))
story.append(Preformatted("""
AssertionEngine.assert_one(assertion, actual_value, context) -> (ok, msg)
输入: assertion(dict), actual_value(dict), context(Context)
输出: (True/False, message)
示例: {"type":"path","path":"data.user.id","operator":"eq","value":"${uid}"}
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/parser.py', styles['SectionCN']))
story.append(Preformatted("""
validate_flow_steps(steps) -> steps
输入: list
输出: list (或抛异常)
示例: validate_flow_steps([...])
""".strip(), styles['CodeCN']))

story.append(Paragraph('dsl/executor.py', styles['SectionCN']))
story.append(Preformatted("""
execute_flow(flow_id, host, host_compare=None) -> dict
输入: flow_id, host, host_compare?
输出: {flow_id, run_id, results}
示例: execute_flow(1, "127.0.0.1:5000")
""".strip(), styles['CodeCN']))

story.append(Paragraph('api/utils.py', styles['SectionCN']))
story.append(Preformatted("""
resolve_params(params_def) -> dict
输入: {"uid":{"type":"fixed","value":10001}, ...}
输出: {"uid":10001,...}

resolve_variables(value, context) -> value
输入: value 含 ${} 引用
输出: 替换后的值

get_value_by_path(obj, path) -> value
输入: obj + "data.items[0].name"
输出: 对应值
""".strip(), styles['CodeCN']))

story.append(Paragraph('tools/http_client.py', styles['SectionCN']))
story.append(Preformatted("""
HttpClient.http_get(url, headers?, params?) -> Response|None
HttpClient.http_post(url, body?, body_type?) -> Response|None
HttpClient.http_put(url, body?, body_type?) -> Response|None
HttpClient.http_delete(url, body?, body_type?) -> Response|None
示例: HttpClient.http_get("http://127.0.0.1:5000/health")
""".strip(), styles['CodeCN']))

story.append(Paragraph('tools/json_validate.py', styles['SectionCN']))
story.append(Preformatted("""
struct_validate_get(tli, schema) -> tli
struct_validate_post(tli, schema, post_body, body_type) -> tli
struct_validate_put(tli, schema, put_body, body_type) -> tli
struct_validate_delete(tli, schema, delete_body, body_type) -> tli
示例: struct_validate_get(tli, schema)
""".strip(), styles['CodeCN']))


doc.build(story)
print('generated api_flowcharts_multi_v4.pdf')
