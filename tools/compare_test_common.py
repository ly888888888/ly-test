import json
import re

from tools.conf import TestResult, TestLogInfo
from tools.http_client import HttpClient, RAWJSON



class JsonCompareResult:
    path = ''
    info = ''
    type = ''


class JSONCompareResultInfo:
    RESULT_PASS = '测试通过'
    TARGET_HAVE_MORE_FIELD = '[对比目标]较[对比标准]多出字段'
    TYPE_NOT_MATCH = '[对比目标]较[对比标准]数据类型不一致'
    TARGET_FIELD_LOST = '[对比目标]较[对比标准]缺少字段'
    FIELD_VALUE_NOT_EQUAL = '[对比目标]较[对比标准]取值不等:'
    FIELD_LEN_NOT_EQUAL = '[对比目标]较[对比标准]数组长度不等'


def removePathArrayIndex(strPath):
    return re.sub(r'\[\d+\]', '[]', strPath)


def compare_field(parent_path, old_value, new_value, lsCompareResults: list, lsIgnore: list):
    curRet = JsonCompareResult()
    curRet.path = parent_path

    if removePathArrayIndex(curRet.path) not in lsIgnore:
        if old_value == new_value:
            curRet.type = TestResult.PASS
            curRet.info = JSONCompareResultInfo.RESULT_PASS

        else:
            ret_info = {
                "对比目标": old_value,
                "对比标准": new_value,
            }
            curRet.info = JSONCompareResultInfo.FIELD_VALUE_NOT_EQUAL + json.dumps(ret_info, ensure_ascii=False)
            curRet.type = TestResult.WARNING

        lsCompareResults.append(curRet)


def compare_list(parent_path, old_list, new_list, lsCompareResults: list, lsIgnore: list):
    if len(old_list) != len(new_list):
        curRet = JsonCompareResult()
        curRet.path = parent_path
        curRet.type = TestResult.WARNING
        curRet.info = JSONCompareResultInfo.FIELD_LEN_NOT_EQUAL
        lsCompareResults.append(curRet)

    len_min = len(new_list) if len(old_list) > len(new_list) else len(old_list)
    for i in range(len_min):
        curRet = JsonCompareResult()
        current_path = parent_path + "[" + str(i) + "]"

        if removePathArrayIndex(curRet.path) not in lsIgnore:
            object_of_old = old_list[i]
            object_of_new = new_list[i]
            if type(object_of_old) == type(object_of_new):
                if type(object_of_old) == dict:
                    compare_dict(current_path, object_of_old, object_of_new, lsCompareResults, lsIgnore)
                elif type(object_of_old) == list:
                    compare_list(current_path, object_of_old, object_of_new, lsCompareResults, lsIgnore)
                else:
                    compare_field(current_path, object_of_old, object_of_new, lsCompareResults, lsIgnore)
            else:
                curRet.type = TestResult.FAIL
                curRet.info = JSONCompareResultInfo.TYPE_NOT_MATCH
                lsCompareResults.append(curRet)


def compare_dict(parent_path, old_dict, new_dict, lsCompareResults: list, lsIgnore: list):
    """
    json中的dict对象对比
    :param parent_path: 父节点路径
    :param old_dict: 对比目标
    :param new_dict: 对比标准
    :param lsCompareResults: 对比结果接收
    :param lsIgnore: 忽略检查的路径列表
    :return:
    """
    old_keys = old_dict.keys()
    new_keys = new_dict.keys()

    for old_key in old_keys:
        curRet = JsonCompareResult()
        current_path = parent_path + "." + old_key
        curRet.path = current_path

        if removePathArrayIndex(curRet.path) not in lsIgnore:
            if old_key in new_keys:  # 对比目标和对比标准中均有此key时
                object_of_old = old_dict[old_key]
                object_of_new = new_dict[old_key]

                if type(object_of_old) == type(object_of_new):
                    if type(object_of_old) == dict:
                        compare_dict(current_path, object_of_old, object_of_new, lsCompareResults, lsIgnore)
                    elif type(object_of_old) == list:
                        compare_list(current_path, object_of_old, object_of_new, lsCompareResults, lsIgnore)
                    else:
                        compare_field(current_path, object_of_old, object_of_new, lsCompareResults, lsIgnore)
                else:
                    curRet.type = TestResult.FAIL
                    curRet.info = JSONCompareResultInfo.TYPE_NOT_MATCH
                    lsCompareResults.append(curRet)

            else:  # 对比目标的key不在对比标准中
                curRet.type = TestResult.NOTICE
                curRet.info = JSONCompareResultInfo.TARGET_HAVE_MORE_FIELD
                lsCompareResults.append(curRet)

    for new_key in new_keys:
        curRet = JsonCompareResult()
        current_path = parent_path + "." + new_key
        curRet.path = current_path

        if removePathArrayIndex(current_path) not in lsIgnore:
            if new_key not in old_keys:
                value_not_equal(new_dict, new_key, current_path, curRet, lsCompareResults)  # 判断对比环境的字段值，是否为空

                # curRet.type = TestResult.FAIL
                # curRet.info = JSONCompareResultInfo.TARGET_FIELD_LOST
                # lsCompareResults.append(curRet)


def compare_url_get(url_old, url_new, case_desc, lsIgnore: list, headers=None):
    result = True
    res_old = HttpClient.http_get(url_old, False, headers=headers)
    res_new = HttpClient.http_get(url_new, False, headers=headers)
    res_old_json = json.loads(res_old.text)
    res_new_json = json.loads(res_new.text)

    lsCompareResult = list()
    compare_dict('root', res_old_json, res_new_json, lsCompareResult, lsIgnore)

    lsTestLogInfo = list()
    lsAssert = list()

    for compare_result in lsCompareResult:
        compare_result: JsonCompareResult = compare_result

        tli = TestLogInfo()
        tli.case_desc = case_desc
        tli.url = url_old
        tli.http_status = res_old.status_code
        tli.test_result = compare_result.type
        tli.error_info = compare_result.path if compare_result.type == TestResult.PASS else \
            '[' + compare_result.path + ']' + compare_result.info

        lsTestLogInfo.append(tli)
        lsAssert.append(tli.test_result)

    if 'FAIL' in lsAssert:
        result = False
    elif 'NOTICE' in lsAssert:
        result = False
    elif 'WARNING' in lsAssert:
        result = False

    for tli in lsTestLogInfo:
        tli.url = url_old
        tli.case_desc = case_desc
        tli.api_id = "对比测试"
        strInfo = '"' + '","'.join([
            str(tli.api_id),
            tli.case_desc.replace(',', '，'),
            str(tli.http_status),
            tli.test_result,
            tli.error_info.replace(',', '，'),
            tli.url
        ]) + '"'


    return lsTestLogInfo, result


def compare_url_post(url_old, url_new, case_desc, lsIgnore: list, headers=None, post_body=None, body_type=RAWJSON):
    result = True
    res_old = HttpClient.http_post(url_old, headers=headers, body=post_body, body_type=body_type, bPrint=False)
    res_new = HttpClient.http_post(url_new, headers=headers, body=post_body, body_type=body_type, bPrint=False)
    res_old_json = json.loads(res_old.text)
    res_new_json = json.loads(res_new.text)

    lsCompareResult = list()
    compare_dict('root', res_old_json, res_new_json, lsCompareResult, lsIgnore)

    lsTestLogInfo = list()
    lsAssert = list()

    for compare_result in lsCompareResult:
        compare_result: JsonCompareResult = compare_result

        tli = TestLogInfo()
        tli.case_desc = case_desc
        tli.url = url_old
        tli.http_status = res_old.status_code
        tli.test_result = compare_result.type
        tli.error_info = compare_result.path if compare_result.type == TestResult.PASS else \
            '[' + compare_result.path + ']' + compare_result.info

        lsTestLogInfo.append(tli)
        lsAssert.append(tli.test_result)

    if 'FAIL' in lsAssert:
        result = False
    elif 'NOTICE' in lsAssert:
        result = False
    elif 'WARNING' in lsAssert:
        result = False

    for tli in lsTestLogInfo:
        tli.url = url_old
        tli.case_desc = case_desc
        tli.api_id = "对比测试"
        strInfo = '"' + '","'.join([
            str(tli.api_id),
            tli.case_desc.replace(',', '，'),
            str(tli.http_status),
            tli.test_result,
            tli.error_info.replace(',', '，'),
            tli.url
        ]) + '"'


    return lsTestLogInfo, result


def value_not_equal(new_dict, new_key, current_path, curRet, lsCompareResults):
    if type(new_dict[new_key]) == str:
        if len(new_dict[new_key]) == 0:
            msg = current_path + "空字符串" + str(new_dict[new_key])
            curRet.type = TestResult.LOST
            curRet.info = JSONCompareResultInfo.TARGET_FIELD_LOST + msg
            lsCompareResults.append(curRet)
        else:
            msg = current_path + "字符串有值" + str(new_dict[new_key])
            curRet.type = TestResult.FAIL
            curRet.info = JSONCompareResultInfo.TARGET_FIELD_LOST + msg
            lsCompareResults.append(curRet)
    elif type(new_dict[new_key]) == int or type(new_dict[new_key]) == float:
        msg = current_path + "数字有值" + str(new_dict[new_key])
        curRet.type = TestResult.FAIL
        curRet.info = JSONCompareResultInfo.TARGET_FIELD_LOST + msg
        lsCompareResults.append(curRet)

    else:
        if bool(new_dict[new_key]):
            msg = current_path + "数组有值" + str(new_dict[new_key])
            curRet.type = TestResult.FAIL
            curRet.info = JSONCompareResultInfo.TARGET_FIELD_LOST + msg
            lsCompareResults.append(curRet)

        else:
            msg = current_path + "空数组" + str(new_dict[new_key])
            curRet.type = TestResult.LOST
            curRet.info = JSONCompareResultInfo.TARGET_FIELD_LOST + msg
            lsCompareResults.append(curRet)


if __name__ == '__main__':
    case_desc = "/edubox/subject/media 返回json双环境对比"
    url_old = "http://172.17.12.100:9500/children/wholewatch/v3?mac=70%3A2E%3AD9%3AE0%3A3D%3A6C&chiptype=638_CVTE&" \
              "brand=CVTE_APP&account_id=1000291445&token=9739401f-5391-3b1b-908c-af975356159d&sid=SMART_TV&model=&" \
              "version=5.9.9.9&edu=2812-4844-2592-2853"
    url_new = "http://172.17.12.100:9501/children/wholewatch/v3?mac=70%3A2E%3AD9%3AE0%3A3D%3A6C&chiptype=638_CVTE&" \
              "brand=CVTE_APP&account_id=1000291445&token=9739401f-5391-3b1b-908c-af975356159d&sid=SMART_TV&model=&" \
              "version=5.9.9.9&edu=2812-4844-2592-2853"
    r = compare_url_get(url_old, url_new, case_desc, [])
