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

from torch.utils.hipify.hipify_python import InputError
from tree_sitter import Parser
from tree_sitter_languages import get_language

class FastReview:
    def __init__(self, language: str = "java"):
        self.parser = Parser()

        if language == "java":
            self.parser.set_language(get_language("java"))
        else:
            raise InputError("Other language are not yet supported.")

    def check_indentation(self, code: str):
        """检查缩进是否为 4 空格，禁止 Tab"""
        errors = []
        for i, line in enumerate(code.splitlines(), start=1):
            if line.strip() == "":
                continue
            if line.startswith(" "):
                spaces = len(line) - len(line.lstrip(" "))
                if spaces % 4 != 0:
                    errors.append(f"Line {i}: Indent is not a multiple of 4 (current) {spaces} Space)")
            elif line.startswith("\t"):
                errors.append(f"Line {i}: Tab indentation used, should be changed to 4 spaces")
        return errors

    def find_functions(self, node, code: str):
        errors = []
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                func_name = code[name_node.start_byte:name_node.end_byte]
                # 只要是合法标识符就检查
                if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', func_name):
                    if not re.match(r'^[a-z_][a-z0-9_]*$', func_name):
                        errors.append(f"function name'{func_name}' Does not comply with snake_case naming conventions")
        for child in node.children:
            errors.extend(self.find_functions(child, code))
        return errors

    def check_function_names(self, tree, code: str):
        """检查函数命名是否符合 snake_case"""
        return self.find_functions(tree.root_node, code)

    def run_checks(self, file_path: str):
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()

        tree = self.parser.parse(code.encode("utf-8"))

        errors = []
        errors.extend(self.check_indentation(code))
        errors.extend(self.check_function_names(tree, code))

        if errors:
            print("❌ Style check reveals issues:")
            for e in errors:
                print(" -", e)
            sys.exit(1)
        else:
            print("✅ Style check passed")


if __name__ == "__main__":
    file_path = "client.py"
    fast_review = FastReview()
    fast_review.run_checks(file_path)
