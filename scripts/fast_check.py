"""
风格检查工具 fast_check.py

1. 缩进检查
    - 遍历每一行代码，如果行首有空格，就统计空格数量。
    - 要求缩进必须是 4 的倍数。
    - 如果不是，就报错：Line X: 缩进不是 4 的倍数
    - 如果使用 Tab 缩进，也报错。

2. 函数命名检查
    - 使用 tree-sitter 解析 Python 语法树。
    - 遍历 AST，找到所有 function_definition 节点。
    - 提取函数名，要求符合 snake_case：
    * 必须以小写字母或下划线开头，后续只能包含小写字母、数字或下划线
    - 如果不符合，就报错：函数名 'xxx' 不符合 snake_case 命名规范
"""

import sys
import re
from tree_sitter import Parser
from tree_sitter_languages import get_language

LANGUAGE = get_language("python")
parser = Parser()
parser.set_language(LANGUAGE)


def check_indentation(code: str):
    """检查缩进是否为 4 空格，禁止 Tab"""
    errors = []
    for i, line in enumerate(code.splitlines(), start=1):
        if line.strip() == "":
            continue
        if line.startswith(" "):
            spaces = len(line) - len(line.lstrip(" "))
            if spaces % 4 != 0:
                errors.append(f"Line {i}: 缩进不是 4 的倍数 (当前 {spaces} 空格)")
        elif line.startswith("\t"):
            errors.append(f"Line {i}: 使用了 Tab 缩进，应改为 4 空格")
    return errors


def find_functions(node, code: str):
    errors = []
    if node.type == "function_definition":
        name_node = node.child_by_field_name("name")
        if name_node:
            func_name = code[name_node.start_byte:name_node.end_byte]
            # 只要是合法标识符就检查
            if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', func_name):
                if not re.match(r'^[a-z_][a-z0-9_]*$', func_name):
                    errors.append(f"函数名'{func_name}' 不符合 snake_case 命名规范")
    for child in node.children:
        errors.extend(find_functions(child, code))
    return errors


def check_function_names(tree, code: str):
    """检查函数命名是否符合 snake_case"""
    return find_functions(tree.root_node, code)


def run_checks(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    tree = parser.parse(code.encode("utf-8"))

    errors = []
    errors.extend(check_indentation(code))
    errors.extend(check_function_names(tree, code))

    if errors:
        print("❌ 风格检查发现问题：")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    else:
        print("✅ 风格检查通过")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python fast_check.py <python_file>")
        sys.exit(1)
    file_path = sys.argv[1]
    print(f"开始检查: {file_path}")
    run_checks(file_path)
