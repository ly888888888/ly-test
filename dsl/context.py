import re

class Context(dict):
    """存储执行过程中的变量，支持嵌套和点号访问"""
    def get_by_path(self, path):
        """从上下文中获取值，支持点号分隔，如 'steps.login.uid'"""
        parts = path.split('.')
        value = self
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value

    def set_by_path(self, path, value):
        """按路径设置值，自动创建中间字典"""
        parts = path.split('.')
        target = self
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value

    def resolve(self, text):
        """解析字符串中的 ${var} 引用"""
        def replacer(match):
            var_path = match.group(1)
            value = self.get_by_path(var_path)
            if value is None:
                raise ValueError(f"变量 {var_path} 不存在")
            return repr(value)  # 用 repr 而不是 str

        return re.sub(r'\$\{([^}]+)\}', replacer, text)

if __name__ == '__main__':
    # context = Context({
    #     "steps": {
    #         "login": {
    #             "uid": 10001
    #         }
    #     }
    # })
    #
    # print(context.get_by_path("steps.login.uid"))

    # context = Context()
    #
    # context.set_by_path("steps.login.uid", 10001)
    # print(context)

    context = Context({
        "token": "abc123",
        "uid": 10001
    })

    text = "Authorization: Bearer ${token}, uid=${uid}"

    result = context.resolve(text)
    print(result)
