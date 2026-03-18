# Auth
Login (default admin) and use `Authorization: Bearer <token>` for protected APIs.

```bash
curl -X POST http://172.17.7.156:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```
#注意:
##1、创建接口定义
```bash
curl -X POST http://172.17.7.156:5000/api/interfaces \
  -H "Content-Type: application/json" \
  -d '{
    "project": "jupiter",
    "path": "/config/homepage/v4",
    "method": "GET",
    "schema": {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "title": "/config/homepage/v4",
      "type": "object",
      "properties": {
        "retCode": {"type": "string"},
        "retMsg": {"type": "string"},
        "data": {
          "type": "object",
          "properties": {
            "config": {
              "type": "object",
              "properties": {
                "is_set": {"type": "boolean"},
                "live_back_time": {"type": "integer"},
                "is_show_score": {"type": "boolean"},
                "is_show_vv": {"type": "boolean"},
                "home_refresh_delay": {"type": "string"},
                "home_refresh_rand": {"type": "integer"},
                "bg_img": {"type": "string"},
                "bg_color": {"type": "string"},
                "ad_id": {"type": "string"},
                "use_orange_sdk": {"type": "boolean"},
                "autoplay_forbid_region": {"type": "string"}
              },
              "required": ["is_set","live_back_time","is_show_score","is_show_vv","home_refresh_delay","home_refresh_rand","bg_img","bg_color","ad_id","use_orange_sdk","autoplay_forbid_region"]
            },
            "items": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "type": {"type": "string"},
                  "name": {"type": "string"},
                  "eng_name": {"type": "string"},
                  "action_template": {"type": "string"},
                  "url": {"type": "string"},
                  "is_default": {"type": "integer"},
                  "is_off": {"type": "integer"},
                  "icon": {"type": "string"},
                  "hide_vip_type": {"type": "integer"},
                  "bg_img": {"type": "string"},
                  "bg_color": {"type": "string"},
                  "more_floor": {"type": "string"}
                },
                "required": ["type","name","eng_name","action_template","url","is_default","is_off","icon","hide_vip_type","bg_img","bg_color","more_floor"]
              }
            }
          },
          "required": ["config","items"]
        }
      },
      "required": ["retCode","retMsg","data"]
    },
    "description": "config/homepage/v4 标准接口"
  }'
```
##2、创建各类测试用例
下面通过 API 逐一创建用例。假设接口ID 10（标准）11（监控专用）

###2.1 冒烟测试 (对应 test_case01_smoke)

```bash
curl -X POST http://172.17.7.156:5000/api/testcases \
  -H "Content-Type: application/json" \
  -d '{
    "project": "jupiter",
    "name": "/config/homepage/v4 冒烟测试",
    "api_id": 10,
    "test_type": "smoke",
    "params": {
      "isencode": {"type": "fixed", "value": 1},
      "auto": {"type": "fixed", "value": "single"}
    },
    "expected_status": 200,
    "enabled": true
  }'
```

###2.2 结构测试 (对应 test_case02_structural)
```bash
curl -X POST http://172.17.7.156:5000/api/testcases \
  -H "Content-Type: application/json" \
  -d '{
    "project": "jupiter",
    "name": "/config/homepage/v4 结构测试",
    "api_id": 10,
    "test_type": "structural",
    "params": {
      "isencode": {"type": "fixed", "value": 1},
      "auto": {"type": "fixed", "value": "single"}
    },
    "enabled": true
  }'
```

###2.3 对比测试 (对应 test_case03_compare)
bash
```bash
curl -X POST http://172.17.7.156:5000/api/testcases \
  -H "Content-Type: application/json" \
  -d '{
    "project": "jupiter",
    "name": "/config/homepage/v4 对比测试",
    "api_id": 10,
    "test_type": "compare",
    "params": {
      "isencode": {"type": "fixed", "value": 1},
      "auto": {"type": "fixed", "value": "single"},
      "op_strategy_ids": {
        "type": "function",
        "function": "getFoStrategy",
        "args": {"num": 20}
      }
    },
    "enabled": true
  }'
```

###2.4 逻辑测试（检验desktop 值）
funshion 品牌期望 desktop=1704 为例

```bash
curl -X POST http://172.17.7.156:5000/api/testcases \
  -H "Content-Type: application/json" \
  -d '{
    "project": "jupiter",
    "name": "/config/homepage/v4 逻辑测试 - funshion desktop=1704",
    "api_id": 10,
    "test_type": "logic",
    "params": {
      "isencode": {"type": "fixed", "value": 1},
      "auto": {"type": "fixed", "value": "single"},
      "brand": {"type": "fixed", "value": "funshion"}
    },
    "assertions": [
        {"type": "path", "path": "data.config.desktop", "operator": "eq", "value": 1704}
      ],
    "enabled": true
  }'
```

对其他品牌和期望值重复此操作，可编写脚本批量生成

###2.5 监控测试（tab 检查）
以品牌funshion 为例，使用自定义函数 check_tabs

```bash
curl -X POST http://172.17.7.156:5000/api/testcases \
  -H "Content-Type: application/json" \
  -d '{
    "project": "jupiter",
    "name": "/config/homepage/v4 监控测试 - funshion tab检�?,
    "api_id": 10,
    "test_type": "monitor",
    "params": {
      "isencode": {"type": "fixed", "value": 1},
      "auto": {"type": "fixed", "value": "single"},
      "brand": {"type": "fixed", "value": "funshion"},
      "version": {"type": "function", "function": "randomVer", "args": {}}
    },
    "assertions": [
        {
          "type": "function",
          "function": "check_tabs",
          "args": {"brand": "funshion", "version": "$ref:version"}
        }
      ],
    "enabled": true
  }'
```

###2.6 监控专用结构测试 (test_case14_control)
使用接口 ID 11

```bash
curl -X POST http://172.17.7.156:5000/api/testcases \
  -H "Content-Type: application/json" \
  -d '{
    "project": "jupiter",
    "name": "/config/homepage/v4 监控结构测试",
    "api_id": 11,
    "test_type": "structural",
    "params": {
      "isencode": {"type": "fixed", "value": 1},
      "auto": {"type": "fixed", "value": "single"}
    },
    "enabled": true
  }'
```


##3、执行测试用例
###3.1 执行单个用例
例如执行逻辑测试用例 ID 30（假设）
```bash
curl -X POST http://172.17.7.156:5000/api/run/testcase/30 \
  -H "Content-Type: application/json" \
  -d '{"host": "172.17.12.101:9500"}'

```

###3.2 执行对比测试
需要传入两个host

```bash
curl -X POST http://172.17.7.156:5000/api/run/testcase/22 \
  -H "Content-Type: application/json" \
  -d '{
    "host": "172.17.12.101:9500",
    "host_compare": "172.17.12.101:9501"
  }'
```

###3.3 执行套件
```bash
curl -X POST http://172.17.7.156:5000/api/run/suite \
  -H "Content-Type: application/json" \
  -d '{
    "case_ids": [20,21,22,30,31],
    "host": "172.17.12.101:9500",
    "host_compare": "172.17.12.101:9501",
    "loop_times": 1
  }'
```

##3.4 查询结果
根据返回run_id 获取详细结果

```bash
curl http://172.17.7.156:5000/api/run/results/<run_id>

```


### 接口权限说明
所有涉及「写入/管理操作」的接口（如新增、修改、删除数据）均需验证身份令牌（token）。
注：上述接口调用示例中未全部携带令牌，实际调用受保护接口时，需通过以下任一方式传入token：
- 请求头方式（推荐）：Authorization: Bearer <token> （将<token>替换为实际登录获取的令牌）
- 请求头方式：X-Token: <token>
- URL参数方式：在接口地址后拼接 ?token=<token>

# Permissions (updated)
```text
- admin
- interface:read, interface:write
- testcase:read, testcase:write
- flow:read, flow:write, flow:execute
- function:read, function:execute
- run:read, run:execute
```


# 新增加api
## Interfaces CRUD
```text
curl http://172.17.7.156:5000/api/interfaces?project=jupiter&path=/config/homepage/v4&method=GET
curl http://172.17.7.156:5000/api/interfaces/10
curl -X PUT http://172.17.7.156:5000/api/interfaces/10 -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"description":"update"}'
curl -X DELETE http://172.17.7.156:5000/api/interfaces/10 -H "Authorization: Bearer <token>"

```

## Testcases CRUD
```text
curl http://172.17.7.156:5000/api/testcases?project=jupiter&api_id=10
curl http://172.17.7.156:5000/api/testcases/30
curl -X PUT http://172.17.7.156:5000/api/testcases/30 -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"enabled":false}'
curl -X DELETE http://172.17.7.156:5000/api/testcases/30 -H "Authorization: Bearer <token>"

```

## Flows
```text
curl http://172.17.7.156:5000/api/flows
curl http://172.17.7.156:5000/api/flows/1
curl -X POST http://172.17.7.156:5000/api/flows -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"name":"demo","steps":[{"name":"step1","api_id":1}]}'
curl -X PUT http://172.17.7.156:5000/api/flows/1 -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"enabled":false}'
curl -X DELETE http://172.17.7.156:5000/api/flows/1 -H "Authorization: Bearer <token>"
curl -X POST http://172.17.7.156:5000/api/flows/1/run -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"host":"172.17.12.101:9500"}'
curl http://172.17.7.156:5000/api/flows/results/<run_id>
```


## Functions
```text
curl http://172.17.7.156:5000/api/functions/ -H "Authorization: Bearer <token>"
curl http://172.17.7.156:5000/api/functions/getFoStrategy -H "Authorization: Bearer <token>"
curl -X POST http://172.17.7.156:5000/api/functions/execute -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"name":"getFoStrategy","args":{"num":20}}'
```

## Users (admin)
```text
curl http://172.17.7.156:5000/api/users -H "Authorization: Bearer <token>"
curl -X POST http://172.17.7.156:5000/api/users -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"username":"u1","password":"p1","permissions":["interface:read"]}'
curl http://172.17.7.156:5000/api/users/1 -H "Authorization: Bearer <token>"
curl -X PUT http://172.17.7.156:5000/api/users/1 -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"permissions":["admin"]}'
curl -X DELETE http://172.17.7.156:5000/api/users/1 -H "Authorization: Bearer <token>"
```
