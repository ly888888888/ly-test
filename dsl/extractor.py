import json
from jsonpath_ng import parse

class Extractor:
    @staticmethod
    def extract(response_json, extract_rules):
        """
        根据提取规则从响应中提取值并返回字典
        extract_rules: {"变量名": "JSONPath表达式"}
        例如: {"token": "$.data.token"}
        """
        result = {}
        for var_name, expr in extract_rules.items():
            jsonpath_expr = parse(expr)
            matches = jsonpath_expr.find(response_json)
            if matches:
                # 取第一个匹配的值
                result[var_name] = matches[0].value
            else:
                result[var_name] = None
        return result

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