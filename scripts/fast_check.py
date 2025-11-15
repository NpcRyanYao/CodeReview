import sys
import re
from tree_sitter import Language, Parser

# 1. 构建 Python 语言库（只需一次，生成 .so 文件）
# 在项目根目录运行一次：
#   Language.build_library(
#       'build/my-languages.so',
#       ['tree-sitter-python']
#   )
# 然后在脚本里加载：
PY_LANGUAGE = Language('build/my-languages.so', 'python')

parser = Parser()
parser.set_language(PY_LANGUAGE)


def check_indentation(code: str):
    """检查缩进是否为 4 空格"""
    errors = []
    for i, line in enumerate(code.splitlines(), start=1):
        if line.startswith(" "):
            spaces = len(line) - len(line.lstrip(" "))
            if spaces % 4 != 0:
                errors.append(f"Line {i}: 缩进不是 4 的倍数")
    return errors


def check_function_names(tree, code: str):
    """检查函数命名是否符合 snake_case"""
    errors = []
    root = tree.root_node
    for node in root.children:
        if node.type == "function_definition":
            # 获取函数名
            name_node = node.child_by_field_name("name")
            if name_node:
                func_name = code[name_node.start_byte:name_node.end_byte]
                if not re.match(r'^[a-z_][a-z0-9_]*$', func_name):
                    errors.append(f"函数名 '{func_name}' 不符合 snake_case 命名规范")
    return errors


def run_checks(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    tree = parser.parse(bytes(code, "utf8"))

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
    run_checks(sys.argv[1])
