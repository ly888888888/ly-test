from flask import Blueprint, jsonify
from api import custom_functions
from flask import request

functions_bp = Blueprint('functions', __name__)

@functions_bp.route('/', methods=['GET'])
def list_functions():
    """返回所有注册函数的可读信息"""
    funcs = custom_functions.get_registered_functions()
    return jsonify(funcs)

@functions_bp.route('/<name>', methods=['GET'])
def get_function_detail(name):
    """返回单个函数的详细信息"""
    func_info = custom_functions._FUNCTION_REGISTRY.get(name)  # 直接访问注册表
    if not func_info:
        return jsonify({"error": "Function not found"}), 404
    return jsonify({
        "name": name,
        "description": func_info["description"],
        "parameters": func_info["parameters"],
        "example": func_info["example"]
    })

@functions_bp.route('/execute', methods=['POST'])
def execute_function_api():
    """
    执行指定函数
    """
    data = request.json
    name = data.get("name")
    args = data.get("args", {})

    try:
        result = custom_functions.execute_function(name, **args)
        return jsonify({
            "success": True,
            "result": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400