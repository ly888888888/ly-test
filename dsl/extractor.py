import re
from jsonpath_ng import parse
from api import custom_functions

class Extractor:
    @staticmethod
    def extract(response_json, extract_rules, context=None):
        """
        根据提取规则从响应中提取值。
        支持三种规则格式：
        1. 普通 JSONPath: {"var": "$.path"}
        2. 函数调用: {"var": "func_name($.path, arg2=value, arg3=${context.var})"}
        3. 直接变量引用: {"var": "${context.var}"}
        """
        result = {}
        for var_name, expr in extract_rules.items():
            if isinstance(expr, str):
                # 1. 先处理变量引用（不以函数调用形式）
                if expr.strip().startswith('${') and expr.strip().endswith('}'):
                    # 直接引用上下文变量
                    if context:
                        result[var_name] = context.resolve(expr)
                    else:
                        result[var_name] = None
                    continue

                # 2. 尝试解析为函数调用，格式如 "random_list($.data.grade_term)" 或 "random_list($.data.grade_term, arg=123)"
                func_match = re.match(r'^(\w+)\((.*)\)$', expr.strip())
                if func_match:
                    func_name = func_match.group(1)
                    args_str = func_match.group(2)
                    # 解析参数：支持位置参数（JSONPath 或变量）和关键字参数
                    args, kwargs = Extractor._parse_func_args(args_str, context)
                    # 获取第一个参数（如果是 JSONPath 表达式）对应的值
                    if args:
                        first_arg = args[0]
                        if isinstance(first_arg, str) and first_arg.startswith('$'):
                            # 是 JSONPath 表达式，从响应中取值
                            jsonpath_expr = parse(first_arg)
                            matches = jsonpath_expr.find(response_json)
                            value = matches[0].value if matches else None
                            args = [value] + args[1:]
                        else:
                            # 其他情况（如已经是解析后的值）保持不变
                            pass
                    # 调用注册的函数
                    func = custom_functions.get_function(func_name)
                    if func:
                        try:
                            result[var_name] = func(*args, **kwargs)
                        except Exception as e:
                            result[var_name] = None
                            print(f"Function {func_name} error: {e}")
                    else:
                        result[var_name] = None
                else:
                    # 3. 普通 JSONPath 表达式（可能也包含变量？通常不需要，但为了完整也可以支持）
                    # 如果 JSONPath 表达式中含有变量，先解析
                    if context and isinstance(expr, str) and '${' in expr:
                        expr = context.resolve(expr)
                    jsonpath_expr = parse(expr)
                    matches = jsonpath_expr.find(response_json)
                    result[var_name] = matches[0].value if matches else None
            elif isinstance(expr, dict):
                # 支持更复杂的提取定义（扩展用），暂不实现
                result[var_name] = None
        return result

    @staticmethod
    def _parse_func_args(args_str, context=None):
        """
        解析函数参数字符串，支持变量替换，返回 (args, kwargs)
        例如: "$.data.id, prefix=${steps.step1.prefix}, suffix='_v1'"
        """
        if not args_str.strip():
            return [], {}
        args = []
        kwargs = {}
        # 简单分割（不支持嵌套括号，但足够用）
        parts = args_str.split(',')
        for part in parts:
            part = part.strip()
            if '=' in part:
                k, v = part.split('=', 1)
                k = k.strip()
                v = v.strip()
                # 对值进行变量解析
                if context and isinstance(v, str) and '${' in v:
                    v = context.resolve(v)
                kwargs[k] = v
            else:
                # 对参数值进行变量解析
                if context and isinstance(part, str) and '${' in part:
                    part = context.resolve(part)
                args.append(part)
        return args, kwargs

if __name__ == '__main__':

    response_json = {
        "status": 200,
        "data": {
            "token": "abc123",
            "user": {"id": 10001, "name": "Alice"}
        }
    }
    extract_rules = {
        "token": "$.data.token",
        "user_id": "$.data.user.id",
        "user_name": "$.data.user.name"
    }

    result = Extractor.extract(response_json, extract_rules)
    print(result)