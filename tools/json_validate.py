import json
from jsonschema import validate, draft7_format_checker, SchemaError, ValidationError
from tools.conf import TestLogInfo, TestAssert
from tools.http_client import HttpClient, RAWJSON


def struct_validate_get(tli: TestLogInfo, json_schema, headers=None):
    res = HttpClient.http_get(tli.url, headers=headers, bPrint=False)
    json_res = json.loads(res.text)

    tli.http_status = res.status_code
    try:
        validate(instance=json_res, schema=json_schema, format_checker=draft7_format_checker)
    except SchemaError as e:
        tli.test_result = TestAssert.fail
        tli.error_info = '.'.join([str(i) for i in e.path]) + ' : ' + e.message
    except ValidationError as e:
        tli.test_result = TestAssert.fail
        tli.error_info = '.'.join([str(i) for i in e.path]) + ' : ' + e.message
    else:
        tli.test_result = TestAssert.success

    return tli


def struct_validate_post(tli: TestLogInfo, json_schema, headers=None, post_body=None, body_type=RAWJSON):
    res = HttpClient.http_post(tli.url, headers=headers, body=post_body, body_type=body_type, bPrint=False)
    json_res = json.loads(res.text)

    tli.http_status = res.status_code
    try:
        validate(instance=json_res, schema=json_schema, format_checker=draft7_format_checker)
    except SchemaError as e:
        tli.test_result = TestAssert.fail
        tli.error_info = '.'.join([str(i) for i in e.path]) + ' : ' + e.message
    except ValidationError as e:
        tli.test_result = TestAssert.fail
        tli.error_info = '.'.join([str(i) for i in e.path]) + ' : ' + e.message
    else:
        tli.test_result = TestAssert.success

    return tli


def struct_validate_delete(tli: TestLogInfo, json_schema, headers=None, delete_body=None, body_type=RAWJSON):
    res = HttpClient.http_delete(tli.url, headers=headers, body=delete_body, body_type=body_type, bPrint=False)
    json_res = json.loads(res.text)

    tli.http_status = res.status_code
    try:
        validate(instance=json_res, schema=json_schema, format_checker=draft7_format_checker)
    except SchemaError as e:
        tli.test_result = TestAssert.fail
        tli.error_info = '.'.join([str(i) for i in e.path]) + ' : ' + e.message
    except ValidationError as e:
        tli.test_result = TestAssert.fail
        tli.error_info = '.'.join([str(i) for i in e.path]) + ' : ' + e.message
    else:
        tli.test_result = TestAssert.success

    return tli


def struct_validate_put(tli: TestLogInfo, json_schema, headers=None, put_body=None, body_type=RAWJSON):
    res = HttpClient.http_put(tli.url, headers=headers, body=put_body, body_type=body_type, bPrint=False)
    json_res = json.loads(res.text)

    tli.http_status = res.status_code
    try:
        validate(instance=json_res, schema=json_schema, format_checker=draft7_format_checker)
    except SchemaError as e:
        tli.test_result = TestAssert.fail
        tli.error_info = '.'.join([str(i) for i in e.path]) + ' : ' + e.message
    except ValidationError as e:
        tli.test_result = TestAssert.fail
        tli.error_info = '.'.join([str(i) for i in e.path]) + ' : ' + e.message
    else:
        tli.test_result = TestAssert.success

    return tli
