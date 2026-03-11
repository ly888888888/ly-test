from api.utils import get_value_by_path, compare_value, resolve_variables
from api.custom_functions import get_function
from jsonpath_ng import parse

class AssertionEngine:
    @staticmethod
    def assert_one(assertion, actual_value, context):
        """执行单个断言，返回 (是否通过, 错误信息)"""
        atype = assertion.get('type')
        if atype == 'path':
            path = assertion['path']
            op = assertion['operator']
            expected = assertion['value']
            # 支持变量引用
            expected = context.resolve(str(expected)) if isinstance(expected, str) else expected
            actual = get_value_by_path(actual_value, path)
            if not compare_value(actual, op, expected):
                return False, f"断言失败: {path} {op} {expected}, 实际值: {actual}"
            return True, ""
        elif atype == 'function':
            func_name = assertion['function']
            func_args = assertion.get('args', {})
            # 解析参数中的变量
            func_args = resolve_variables(func_args, context)
            func = get_function(func_name)  # 从注册表获取
            if func:
                try:
                    ok, msg = func(actual_value, **func_args)
                    return ok, msg
                except Exception as e:
                    return False, f"函数执行异常: {str(e)}"
            else:
                return False, f"函数 {func_name} 未找到"
        elif atype == 'jsonpath':
            # 支持 JSONPath 断言
            expr = assertion['jsonpath']
            op = assertion['operator']
            expected = assertion['value']
            jsonpath_expr = parse(expr)
            matches = jsonpath_expr.find(actual_value)
            actual = [m.value for m in matches]
            # 根据操作符比较
            if op == 'eq' and len(actual) == 1:
                return compare_value(actual[0], 'eq', expected), f"JSONPath {expr} 值 {actual[0]} != {expected}"
            elif op == 'contains':
                return expected in actual, f"JSONPath {expr} 不包含 {expected}"
            # 更多操作符...
            else:
                return False, f"不支持的JSONPath断言操作符: {op}"
        else:
            return False, f"未知断言类型: {atype}"