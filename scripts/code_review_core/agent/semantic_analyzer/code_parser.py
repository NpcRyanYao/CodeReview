import os
import re
import hashlib
from typing import List, Dict, Any, Tuple
from .data_models import CodeChange, FunctionSnippet


class CodeParser:
    """代码解析器 - 负责Git解析和代码提取"""

    def __init__(self):
        self.supported_extensions = ['.py', '.java', '.js', '.cpp', '.c', '.go', '.ts']
        self.language_map = {
            '.py': 'python',
            '.java': 'java',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go'
        }

    def parse_git_diff(self, diff_text: str) -> List[CodeChange]:
        """解析git diff输出 - 修复版"""
        changes = []
        lines = diff_text.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            # 检测文件变更头
            if line.startswith('diff --git'):
                file_change = self._parse_file_change_fixed(lines, i)
                if file_change:
                    changes.append(file_change)
                    # 移动到下一个变更块
                    i = self._find_next_diff_index(lines, i)
                else:
                    i += 1
            else:
                i += 1

        return changes

    def _find_next_diff_index(self, lines: List[str], current_index: int) -> int:
        """找到下一个diff开始的位置"""
        i = current_index + 1
        while i < len(lines):
            if lines[i].startswith('diff --git'):
                return i
            i += 1
        return len(lines)

    def _parse_file_change_fixed(self, lines: List[str], start_index: int) -> CodeChange:
        """修复版的文件变更解析"""
        file_path = None
        change_type = 'modified'
        old_content = []
        new_content = []
        line_range = (0, 0)

        i = start_index
        in_hunk = False
        is_deleted_file = False
        is_new_file = False

        while i < len(lines):
            line = lines[i]

            # 检测是否到了下一个diff
            if i > start_index and line.startswith('diff --git'):
                break

            # 检查文件删除标记
            if line.startswith('deleted file mode'):
                is_deleted_file = True
                change_type = 'deleted'

            # 检查文件新增标记
            if line.startswith('new file mode'):
                is_new_file = True
                change_type = 'added'

            # 提取文件路径
            if line.startswith('--- '):
                old_path = line[4:].strip()
                if old_path != '/dev/null':
                    file_path_match = re.search(r'[ab]/(.+)', old_path)
                    if file_path_match:
                        file_path = self._normalize_file_path(file_path_match.group(1))
                        # 如果旧文件路径存在但新文件是/dev/null，则是删除
                        if '+++ /dev/null' in '\n'.join(lines[i:i + 3]):
                            change_type = 'deleted'

            elif line.startswith('+++ '):
                new_path = line[4:].strip()
                if new_path != '/dev/null':
                    file_path_match = re.search(r'[ab]/(.+)', new_path)
                    if file_path_match:
                        file_path = self._normalize_file_path(file_path_match.group(1))
                        # 如果新文件路径存在但旧文件是/dev/null，则是新增
                        if '--- /dev/null' in '\n'.join(lines[i - 3:i]):
                            change_type = 'added'

            # 解析变更块头
            elif line.startswith('@@'):
                hunk_match = re.search(r'@@ -\d+,\d+ \+(\d+),(\d+) @@', line)
                if hunk_match:
                    start_line = int(hunk_match.group(1))
                    line_count = int(hunk_match.group(2))
                    line_range = (start_line, start_line + line_count)
                    in_hunk = True

            # 收集变更内容
            elif in_hunk:
                if line.startswith('-') and not line.startswith('--'):
                    old_content.append(line[1:])
                elif line.startswith('+') and not line.startswith('++'):
                    new_content.append(line[1:])
                elif line.startswith(' '):
                    old_content.append(line[1:])
                    new_content.append(line[1:])
                elif line.startswith('\\'):  # 忽略行结束标记
                    pass

            i += 1

        if not file_path:
            return None

        # 最终确定变更类型
        if is_deleted_file or (old_content and not new_content and '--- /dev/null' not in '\n'.join(
                lines[start_index:start_index + 10])):
            change_type = 'deleted'
        elif is_new_file or (new_content and not old_content and '+++ /dev/null' not in '\n'.join(
                lines[start_index:start_index + 10])):
            change_type = 'added'

        return CodeChange(
            file_path=file_path,
            change_type=change_type,
            old_content='\n'.join(old_content),
            new_content='\n'.join(new_content),
            line_range=line_range
        )

    def extract_functions_from_diff(self, diff_text: str) -> List[FunctionSnippet]:
        """从git diff中提取函数级代码块"""
        changes = self.parse_git_diff(diff_text)
        functions = []

        for change in changes:
            print(f"Processing change: {change.file_path} ({change.change_type})")
            if change.change_type != 'deleted':
                # 对于新增和修改的文件，使用新内容提取函数
                file_functions = self._extract_functions_from_code(
                    change.new_content,
                    change.file_path
                )
                functions.extend(file_functions)
                print(f"Extracted {len(file_functions)} functions from {change.file_path}")

        return functions

    def extract_functions_from_files(self, file_paths: List[str]) -> List[FunctionSnippet]:
        """从文件列表中提取所有函数"""
        functions = []

        for file_path in file_paths:
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                file_functions = self._extract_functions_from_code(content, file_path)
                functions.extend(file_functions)
                print(f"Extracted {len(file_functions)} functions from {file_path}")
            except Exception as e:
                print(f"Error processing {file_path}: {e}")

        return functions

    def scan_directory(self, directory_path: str) -> List[str]:
        """扫描目录，返回所有代码文件路径"""
        code_files = []

        if not os.path.exists(directory_path):
            print(f"Directory not found: {directory_path}")
            return code_files

        for root, dirs, files in os.walk(directory_path):
            # 忽略隐藏目录和虚拟环境
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]

            for file in files:
                if any(file.endswith(ext) for ext in self.supported_extensions):
                    full_path = os.path.join(root, file)
                    code_files.append(full_path)

        print(f"Scanned {len(code_files)} code files in {directory_path}")
        return code_files

    def get_total_file_count(self, directories: List[str]) -> int:
        """获取源代码目录中的总文件数"""
        total_count = 0
        for directory in directories:
            code_files = self.scan_directory(directory)
            total_count += len(code_files)
        return total_count

    def detect_language(self, file_path: str) -> str:
        """根据文件扩展名检测编程语言"""
        ext = os.path.splitext(file_path)[1].lower()
        return self.language_map.get(ext, 'unknown')

    def _extract_functions_from_code(self, code_text: str, file_path: str) -> List[FunctionSnippet]:
        """从代码文本中提取函数"""
        language = self.detect_language(file_path)

        if language == 'python':
            return self._extract_python_functions(code_text, file_path)
        elif language == 'java':
            return self._extract_java_functions(code_text, file_path)
        elif language in ['javascript', 'typescript']:
            return self._extract_javascript_functions(code_text, file_path)
        else:
            return self._extract_generic_functions(code_text, file_path, language)

    def _extract_python_functions(self, code_text: str, file_path: str) -> List[FunctionSnippet]:
        """提取Python函数"""
        functions = []
        lines = code_text.split('\n')

        current_function = None
        start_line = 0
        function_lines = []
        indent_level = 0

        for i, line in enumerate(lines):
            line_num = i + 1
            stripped = line.strip()

            # 检测函数定义
            if stripped.startswith('def ') and not current_function:
                # 提取函数名
                func_match = re.match(r'def\s+(\w+)\s*\(', stripped)
                if func_match:
                    current_function = func_match.group(1)
                    start_line = line_num
                    function_lines = [line]
                    indent_level = len(line) - len(line.lstrip())

            elif current_function:
                # 检查是否还在函数内
                if line.strip() and (len(line) - len(line.lstrip())) > indent_level:
                    function_lines.append(line)
                else:
                    # 函数结束
                    if len(function_lines) > 1:  # 至少要有函数定义和内容
                        function_code = '\n'.join(function_lines)
                        function_id = self._generate_function_id(file_path, current_function, start_line)

                        functions.append(FunctionSnippet(
                            id=function_id,
                            name=current_function,
                            code=function_code,
                            file_path=self._normalize_file_path(file_path),
                            start_line=start_line,
                            end_line=line_num - 1,
                            language='python',
                            metadata={'type': 'function'}
                        ))

                    current_function = None
                    function_lines = []

                    # 检查当前行是否是新函数的开始
                    if stripped.startswith('def '):
                        func_match = re.match(r'def\s+(\w+)\s*\(', stripped)
                        if func_match:
                            current_function = func_match.group(1)
                            start_line = line_num
                            function_lines = [line]
                            indent_level = len(line) - len(line.lstrip())

        # 处理最后一个函数
        if current_function and function_lines:
            function_code = '\n'.join(function_lines)
            function_id = self._generate_function_id(file_path, current_function, start_line)

            functions.append(FunctionSnippet(
                id=function_id,
                name=current_function,
                code=function_code,
                file_path=self._normalize_file_path(file_path),
                start_line=start_line,
                end_line=len(lines),
                language='python',
                metadata={'type': 'function'}
            ))

        return functions

    def _extract_java_functions(self, code_text: str, file_path: str) -> List[FunctionSnippet]:
        """提取Java函数"""
        # 简化的Java方法提取实现
        return self._extract_generic_functions(code_text, file_path, 'java')

    def _extract_javascript_functions(self, code_text: str, file_path: str) -> List[FunctionSnippet]:
        """提取JavaScript/TypeScript函数"""
        # 简化的JS函数提取实现
        return self._extract_generic_functions(code_text, file_path, 'javascript')

    def _extract_generic_functions(self, code_text: str, file_path: str, language: str) -> List[FunctionSnippet]:
        """通用函数提取（用于不支持的语言）"""
        # 简单地将整个代码作为一个函数返回
        lines = code_text.split('\n')
        if not lines or not code_text.strip():
            return []

        function_id = self._generate_function_id(file_path, 'main', 1)

        return [FunctionSnippet(
            id=function_id,
            name='main',
            code=code_text,
            file_path=self._normalize_file_path(file_path),
            start_line=1,
            end_line=len(lines),
            language=language,
            metadata={'type': 'file'}
        )]

    def _generate_function_id(self, file_path: str, function_name: str, start_line: int) -> str:
        """生成函数唯一ID"""
        normalized_path = self._normalize_file_path(file_path)
        unique_string = f"{normalized_path}:{function_name}:{start_line}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:16]

    def _normalize_file_path(self, file_path: str) -> str:
        """规范化文件路径格式"""
        # 统一使用相对路径和正斜杠
        normalized = file_path.replace('\\', '/')
        if normalized.startswith('./'):
            normalized = normalized[2:]
        return normalized