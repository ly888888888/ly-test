import random
import inspect
from tools.conf import TestDB

# 注册表结构：name -> {"func": func, "description": str, "parameters": list, "example": str}
_FUNCTION_REGISTRY = {}

def register(func):
    """装饰器：将函数注册到注册表，并提取可读信息"""
    sig = inspect.signature(func)
    param_names = list(sig.parameters.keys())
    # 生成示例，如：函数名(参数1=?, 参数2=?)
    example = f"{func.__name__}({', '.join([f'{name}=?' for name in param_names])})"
    _FUNCTION_REGISTRY[func.__name__] = {
        "func": func,
        "description": inspect.getdoc(func) or "",
        "parameters": param_names,
        "example": example
    }
    return func

def get_registered_functions():
    """返回所有注册函数的可读信息列表"""
    result = []
    for name, info in _FUNCTION_REGISTRY.items():
        result.append({
            "name": name,
            "description": info["description"],
            "parameters": info["parameters"],
            "example": info["example"]
        })
    return result

def get_function(name):
    """根据名称获取可调用的函数对象"""
    info = _FUNCTION_REGISTRY.get(name)
    return info["func"] if info else None

def execute_function(name, **kwargs):
    """
    根据函数名执行注册函数
    """
    info = _FUNCTION_REGISTRY.get(name)

    if not info:
        raise ValueError(f"Function {name} not registered")

    func = info["func"]

    try:
        result = func(**kwargs)
        return result
    except Exception as e:
        raise RuntimeError(f"Function {name} execution failed: {e}")

@register
def getFoStrategy(num):
    """
    从 fo_strategy 表随机获取指定数量可用的 strategy_id，返回逗号分隔字符串
    """
    connection = TestDB.get_connection()
    try:
        with connection.cursor() as cursor:
            sql = f"SELECT strategy_id FROM db_jupiter_operation.fo_strategy WHERE `disable` = 0 ORDER BY RAND() LIMIT {num}"
            cursor.execute(sql)
            results = cursor.fetchall()
            ids = [str(i[0]) for i in results]
            return ",".join(ids)
    finally:
        connection.close()

@register
def randomVer():
    """从列表里面随机取一个版本号"""
    versions = ["5.3.8.4", "5.1.3.8", "5.1.7.8", "6.1.0.8", "5.2.6.8", "5.4.9.1"]
    return random.choice(versions)

@register
def check_tabs(response_json, brand, version):
    """
    监控测试专用：根据品牌和版本检查 items 中的 tab 是否符合预期
    返回 (是否通过, 错误信息)
    """
    ver_float = float(version[:3])
    items = response_json.get('data', {}).get('items', [])
    item_names = [item.get('name', '') for item in items]
    missing = []

    if ver_float < 5.2:
        expected = ['搜索', '视频', '应用']
    elif 5.2 <= ver_float <= 5.9:
        if brand == "funshion":
            expected = ['搜索', '首页', '风行金卡', '应用']
        else:
            expected = ['搜索', '首页', '应用']
    else:
        return True, ""

    for e in expected:
        if e not in item_names:
            missing.append(e)

    if missing:
        return False, f"缺少tab: {missing}"
    return True, ""


if __name__ == '__main__':
    print(randomVer())