from jsonpath_ng import parse

from api.custom_functions import get_function
from api.utils import get_value_by_path, compare_value, resolve_variables

class AssertionEngine:
    @staticmethod
    def assert_one(assertion, actual_value, context):
        """Execute one assertion and return (ok, message)."""
        atype = assertion.get('type')
        if atype == 'path':
            path = assertion['path']
            op = assertion['operator']
            expected = assertion['value']
            # Support variable references
            expected = context.resolve(str(expected)) if isinstance(expected, str) else expected
            actual = get_value_by_path(actual_value, path)
            if not compare_value(actual, op, expected):
                return False, f"Assertion failed: {path} {op} {expected}, actual={actual}"
            return True, ""
        elif atype == 'function':
            func_name = assertion['function']
            func_args = assertion.get('args', {})
            func_args = resolve_variables(func_args, context)
            func = get_function(func_name)
            if func:
                try:
                    ok, msg = func(actual_value, **func_args)
                    return ok, msg
                except Exception as e:
                    return False, f"Function execution error: {str(e)}"
            else:
                return False, f"Function {func_name} not found"
        elif atype == 'jsonpath':
            expr = assertion['jsonpath']
            op = assertion['operator']
            expected = assertion['value']
            jsonpath_expr = parse(expr)
            matches = jsonpath_expr.find(actual_value)
            actual = [m.value for m in matches]
            if op == 'eq' and len(actual) == 1:
                return compare_value(actual[0], 'eq', expected), f"JSONPath {expr} value {actual[0]} != {expected}"
            elif op == 'contains':
                return expected in actual, f"JSONPath {expr} does not contain {expected}"
            else:
                return False, f"Unsupported JSONPath operator: {op}"
        else:
            return False, f"Unknown assertion type: {atype}"
