import time
import os
import re
import hashlib
from typing import List, Dict, Any, Tuple
from .data_models import AnalysisResult, FunctionSnippet, SearchResult
from .code_parser import CodeParser
from .vector_manager import VectorManager


class SemanticAnalyzer:
    """语义分析器 - 主控制器"""

    def __init__(self, source_directories: List[str] = None,
                 model_name: str = "microsoft/codebert-base"):
        self.source_directories = source_directories or ['.']
        self.parser = CodeParser()
        self.vector_manager = VectorManager(model_name)
        self.rebuild_threshold = 0.3
        self.min_files_for_rebuild = 10

    def analyze(self, git_diff: str) -> AnalysisResult:
        """执行语义分析 - 重构版：逐个函数处理"""
        start_time = time.time()
        all_similar_functions = []
        processed_functions = []

        try:
            # 1. 解析git diff，判断是否需要全量重建
            changed_files = self.parser.parse_git_diff(git_diff)
            total_files = self.parser.get_total_file_count(self.source_directories)

            print(f"Changed files: {len(changed_files)}, Total files: {total_files}")

            rebuild_required = self._should_rebuild_database(changed_files, total_files)

            if rebuild_required:
                print("Triggering full rebuild due to significant changes")
                return self._perform_full_rebuild_analysis()

            # 2. 逐个处理每个变更
            print("Performing incremental update with per-function processing")

            # 处理删除的文件
            deleted_function_ids = self._identify_deleted_functions(changed_files)
            if deleted_function_ids:
                print(f"Deleting {len(deleted_function_ids)} functions from deleted files")
                self.vector_manager.delete_functions(deleted_function_ids)

            # 处理新增和修改的文件
            for change in changed_files:
                if change.change_type != 'deleted':
                    print(f"\n--- Processing {change.file_path} ({change.change_type}) ---")

                    # 提取该文件的所有函数
                    file_functions = self._extract_functions_from_content(change.new_content, change.file_path)

                    for function in file_functions:
                        print(f"\n🔍 Processing function: {function.name}")

                        # 对每个函数进行检索
                        similar_results = self.vector_manager.search_by_function(function, top_k=3)
                        all_similar_functions.extend(similar_results)

                        # 记录处理过的函数
                        processed_functions.append(function)

                        # 显示检索结果
                        if similar_results:
                            print(f"   Found {len(similar_results)} similar functions:")
                            for i, result in enumerate(similar_results[:2]):
                                print(f"     {i + 1}. {result.function.name} (score: {result.similarity_score:.3f})")
                        else:
                            print("   No similar functions found")

            # 3. 批量更新数据库（处理过的所有函数）
            if processed_functions:
                print(f"\n📦 Batch updating {len(processed_functions)} functions in database...")
                vectors = self.vector_manager.encode_functions(processed_functions)
                self.vector_manager.update_functions(processed_functions, vectors)
                print(f"✅ Successfully updated {len(processed_functions)} functions")

            # 4. 整合分析结果
            duration_ms = (time.time() - start_time) * 1000

            return AnalysisResult(
                analysis_type="semantic",
                duration_ms=duration_ms,
                similar_functions=all_similar_functions,
                changed_functions=processed_functions,
                rebuild_required=False,
                total_files_processed=len(processed_functions),
                deleted_functions_count=len(deleted_function_ids)
            )

        except Exception as e:
            print(f"Analysis error: {e}")
            import traceback
            traceback.print_exc()
            duration_ms = (time.time() - start_time) * 1000
            return AnalysisResult(
                analysis_type="semantic",
                duration_ms=duration_ms,
                similar_functions=[],
                changed_functions=[],
                rebuild_required=False,
                total_files_processed=0,
                deleted_functions_count=0
            )

    def _perform_full_rebuild_analysis(self) -> AnalysisResult:
        """执行全量重建并返回分析结果"""
        start_time = time.time()

        print("Performing full rebuild...")
        all_functions = self._perform_full_rebuild()

        # 对重建后的函数进行相似性分析
        all_similar_functions = []
        print("\n🔍 Analyzing similarities after rebuild...")

        for i, function in enumerate(all_functions[:10]):  # 只分析前10个函数避免耗时过长
            print(f"  Analyzing {function.name}...")
            similar_results = self.vector_manager.search_by_function(function, top_k=2)
            all_similar_functions.extend(similar_results)

        duration_ms = (time.time() - start_time) * 1000

        return AnalysisResult(
            analysis_type="semantic_rebuild",
            duration_ms=duration_ms,
            similar_functions=all_similar_functions,
            changed_functions=all_functions,
            rebuild_required=True,
            total_files_processed=len(all_functions),
            deleted_functions_count=0
        )

    def _identify_deleted_functions(self, changed_files: List) -> List[str]:
        """识别已删除文件中的函数ID"""
        deleted_function_ids = []

        for change in changed_files:
            print(f"Checking change: {change.file_path} - type: {change.change_type}")

            if change.change_type == 'deleted':
                print(f"Found deleted file: {change.file_path}")

                # 从旧内容中提取函数ID
                if change.old_content.strip():
                    try:
                        old_functions = self._extract_functions_from_content(change.old_content, change.file_path)
                        for func in old_functions:
                            deleted_function_ids.append(func.id)
                            print(f"Marked for deletion from old content: {func.name} (id: {func.id})")
                    except Exception as e:
                        print(f"Failed to extract functions from old content: {e}")

                # 从数据库中查找该文件的所有函数
                db_function_ids = self._find_functions_by_file_path(change.file_path)
                for func_id in db_function_ids:
                    if func_id not in deleted_function_ids:
                        deleted_function_ids.append(func_id)
                        print(f"Marked for deletion from database: {func_id}")

        print(f"Total {len(deleted_function_ids)} functions marked for deletion")
        return deleted_function_ids

    def _extract_functions_from_content(self, content: str, file_path: str) -> List[FunctionSnippet]:
        """从内容中提取函数（不依赖文件存在）"""
        language = self.parser.detect_language(file_path)

        if language == 'python':
            return self._extract_python_functions_from_content(content, file_path)
        else:
            # 通用提取
            lines = content.split('\n')
            function_id = self._generate_function_id(file_path, 'main', 1)
            return [FunctionSnippet(
                id=function_id,
                name='main',
                code=content,
                file_path=file_path,
                start_line=1,
                end_line=len(lines),
                language=language,
                metadata={'type': 'file'}
            )]

    def _extract_python_functions_from_content(self, content: str, file_path: str) -> List[FunctionSnippet]:
        """从Python内容中提取函数"""
        functions = []
        lines = content.split('\n')

        current_function = None
        start_line = 0
        function_lines = []
        indent_level = 0

        for i, line in enumerate(lines):
            line_num = i + 1
            stripped = line.strip()

            # 检测函数定义
            if stripped.startswith('def ') and not current_function:
                func_match = re.match(r'def\s+(\w+)\s*\(', stripped)
                if func_match:
                    current_function = func_match.group(1)
                    start_line = line_num
                    function_lines = [line]
                    indent_level = len(line) - len(line.lstrip())

            elif current_function:
                # 检查是否还在函数内
                current_indent = len(line) - len(line.lstrip()) if line.strip() else indent_level

                if current_indent > indent_level or not line.strip():
                    function_lines.append(line)
                else:
                    # 函数结束
                    if len(function_lines) > 0:
                        function_code = '\n'.join(function_lines)
                        function_id = self._generate_function_id(file_path, current_function, start_line)

                        functions.append(FunctionSnippet(
                            id=function_id,
                            name=current_function,
                            code=function_code,
                            file_path=file_path,
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
                file_path=file_path,
                start_line=start_line,
                end_line=len(lines),
                language='python',
                metadata={'type': 'function'}
            ))

        return functions

    def _generate_function_id(self, file_path: str, function_name: str, start_line: int) -> str:
        """生成函数唯一ID"""
        normalized_path = file_path.replace('\\', '/')
        if normalized_path.startswith('./'):
            normalized_path = normalized_path[2:]
        unique_string = f"{normalized_path}:{function_name}:{start_line}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:16]

    def _find_functions_by_file_path(self, file_path: str) -> List[str]:
        """从数据库中查找指定文件路径的所有函数ID"""
        try:
            normalized_path = file_path.replace('\\', '/')
            if normalized_path.startswith('./'):
                normalized_path = normalized_path[2:]

            print(f"Searching database for file: {normalized_path}")

            if hasattr(self.vector_manager.collection, 'get'):
                all_data = self.vector_manager.collection.get()
                matching_ids = []

                for i, metadata in enumerate(all_data['metadatas']):
                    db_file_path = metadata.get('file_path', '')
                    if db_file_path == normalized_path:
                        matching_ids.append(all_data['ids'][i])
                        print(f"Found matching function: {all_data['ids'][i]} - {metadata.get('name', 'unknown')}")

                return matching_ids

        except Exception as e:
            print(f"Error finding functions by file path: {e}")

        return []

    def _should_rebuild_database(self, changed_files: List, total_files: int) -> bool:
        """基于变更文件比例判断是否需要全量重建"""
        if total_files == 0:
            return True

        if total_files < self.min_files_for_rebuild:
            print(
                f"Total files ({total_files}) less than minimum ({self.min_files_for_rebuild}), using incremental update")
            return False

        changed_ratio = len(changed_files) / total_files
        print(f"Changed ratio: {changed_ratio:.2f} ({len(changed_files)}/{total_files})")

        rebuild_needed = changed_ratio > self.rebuild_threshold
        if rebuild_needed:
            print(f"Rebuild triggered: changed ratio {changed_ratio:.2f} > threshold {self.rebuild_threshold}")
        else:
            print(f"Incremental update: changed ratio {changed_ratio:.2f} <= threshold {self.rebuild_threshold}")

        return rebuild_needed

    def _perform_incremental_update(self, git_diff: str) -> List[FunctionSnippet]:
        """执行增量更新"""
        changed_functions = self.parser.extract_functions_from_diff(git_diff)

        if not changed_functions:
            print("No functions extracted from diff")
            return []

        print(f"Extracted {len(changed_functions)} functions from diff")

        vectors = self.vector_manager.encode_functions(changed_functions)
        self.vector_manager.update_functions(changed_functions, vectors)

        return changed_functions

    def _perform_full_rebuild(self) -> List[FunctionSnippet]:
        """执行全量重建"""
        all_files = []
        for directory in self.source_directories:
            directory_files = self.parser.scan_directory(directory)
            all_files.extend(directory_files)

        print(f"Found {len(all_files)} code files for rebuild")

        all_functions = self.parser.extract_functions_from_files(all_files)

        if not all_functions:
            print("No functions extracted during rebuild")
            return []

        print(f"Extracted {len(all_functions)} functions for rebuild")

        self.vector_manager.clear_database()

        print("Encoding functions...")
        vectors = self.vector_manager.encode_functions(all_functions)

        print("Storing functions to database...")
        self.vector_manager.store_functions(all_functions, vectors)

        return all_functions

    def rebuild_database(self) -> bool:
        """手动触发全量重建"""
        try:
            self._perform_full_rebuild()
            return True
        except Exception as e:
            print(f"Rebuild error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def search_similar_code(self, code_snippet: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索相似代码"""
        temp_function = FunctionSnippet(
            id="query",
            name="query_function",
            code=code_snippet,
            file_path="query.py",
            start_line=1,
            end_line=len(code_snippet.split('\n')),
            language="python",
            metadata={}
        )

        results = self.vector_manager.search_by_function(temp_function, top_k)

        return [{
            'function_name': result.function.name,
            'file_path': result.function.file_path,
            'similarity_score': round(result.similarity_score, 4),
            'code_snippet': result.function.code[:200] + "..." if len(
                result.function.code) > 200 else result.function.code
        } for result in results]

    def get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息"""
        return self.vector_manager.get_database_stats()

    def set_rebuild_threshold(self, threshold: float):
        """设置重建阈值"""
        self.rebuild_threshold = threshold
        print(f"Rebuild threshold set to: {threshold}")

    def close(self):
        """释放所有资源"""
        try:
            if hasattr(self, 'vector_manager'):
                self.vector_manager.close()
            print("All resources released")
        except Exception as e:
            print(f"Error closing analyzer: {e}")