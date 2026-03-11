from tools.conf import TestDB  # 复用原有数据库连接
from api import custom_functions

def resolve_params(params_def):
    """
    根据 params 定义（JSON）解析出真实的请求参数字典
    :param params_def: 例如 {"id": {"type": "db_query", "sql": "SELECT ..."}, "isencode": {"type": "fixed", "value": 1}}
    :return: dict 例如 {"id": 12345, "isencode": 1}
    """
    resolved = {}
    for key, def_item in params_def.items():
        if not isinstance(def_item, dict):
            print(f"Skip non-dict field: {key}")
            continue
        typ = def_item.get('type')
        if typ == 'fixed':
            resolved[key] = def_item['value']
        elif typ == 'db_query':
            sql = def_item['sql']
            # 执行查询，仅取第一条记录第一列
            conn = TestDB.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql)
                    result = cursor.fetchone()
                    resolved[key] = result[0] if result else None
            finally:
                conn.close()
        elif typ == 'function':
            func_name = def_item['function']
            args = def_item.get('args', {})
            func = getattr(custom_functions, func_name, None)
            if func is None:
                raise ValueError(f"Function {func_name} not found")
            resolved[key] = func(**args)
        elif typ == 'random':
            # 实现随机生成逻辑，这里略
            resolved[key] = 'random_value'
        else:
            raise ValueError(f'Unknown param type: {typ}')
    return resolved

def get_value_by_path(obj, path):
    """
    通过点分路径从 JSON 对象中取值，支持数组索引，如 "data.items[0].name" 或 "data.0.name"
    """
    parts = path.split('.')
    current = obj
    for part in parts:
        if current is None:
            return None

        # 处理方括号格式，如 "data[0]"
        if '[' in part and ']' in part:
            # 分割字段名和索引，例如 "data[0]" -> name="data", idx="0"
            name, idx = part.split('[')
            idx = int(idx.strip(']'))
            if name:  # 如果字段名存在，先按字典取值
                if not isinstance(current, dict):
                    return None
                current = current.get(name)
                if current is None:
                    return None
            # 再按列表索引取值
            if not isinstance(current, list):
                return None
            if idx < 0 or idx >= len(current):
                return None
            current = current[idx]

        else:
            # 处理普通字段名或数字索引（如 "data.0" 中的 "0"）
            # 如果当前节点是列表且 part 是纯数字，则视为数组索引
            if isinstance(current, list) and part.isdigit():
                idx = int(part)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                # 当前节点类型不匹配
                return None

    return current

def resolve_variables(value, context):
    """递归解析值中的变量引用"""
    if isinstance(value, str):
        return context.resolve(value)
    elif isinstance(value, dict):
        return {k: resolve_variables(v, context) for k, v in value.items()}
    elif isinstance(value, list):
        return [resolve_variables(item, context) for item in value]
    else:
        return value

def compare_value(actual, operator, expected):
    if operator == 'eq':
        return actual == expected
    elif operator == 'ne':
        return actual != expected
    elif operator == 'gt':
        return actual > expected
    elif operator == 'lt':
        return actual < expected
    elif operator == 'ge':
        return actual >= expected
    elif operator == 'le':
        return actual <= expected
    elif operator == 'contains':
        return expected in actual
    # 可根据需要扩展
    return False

if __name__ == '__main__':
    # print(resolve_params({
    #   "isencode": {"type": "fixed", "value": 1},
    #   "auto": {"type": "fixed", "value": "single"},
    #   "brand": {"type": "fixed", "value": "funshion"},
    #   "_assertions": [
    #     {"type": "path", "path": "data.config.desktop", "operator": "eq", "value": 1704}
    #   ]
    # }))
    # print(resolve_params({
    #   "isencode": {"type": "fixed", "value": 1},
    #   "auto": {"type": "fixed", "value": "single"},
    #   "brand": {"type": "fixed", "value": "funshion"},
    #   "version": {"type": "function", "function": "randomVer", "args": {}},
    #   "_assertions": [
    #     {
    #       "type": "function",
    #       "function": "check_tabs",
    #       "args": {"brand": "funshion", "version": {"$ref": "version"}}  # 注意：这里需要引用 version 的值
    #     }
    #   ]
    # }))

    response = {
        "data": {
            "items": [
                {"name": "apple", "price": 10},
                {"name": "banana", "price": 20}
            ]
        }
    }
    print(get_value_by_path(response, "data.items[0].name"))
