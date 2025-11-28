"""代码诊断工具"""
import asyncio
import os
from typing import List, Dict, Any, Union
from pathlib import Path

try:
    from .server_manager import ServerManager
    from .lsp_client import LSPClient
    from .lsp_types import Diagnostic
except ImportError:
    from .server_manager import ServerManager
    from .lsp_client import LSPClient
    from .lsp_types import Diagnostic


class CodeDiagnosticTool:
    """代码诊断工具
    支持项目级分析，确保有完整的上下文
    """
    def __init__(self):
        self.server_manager = ServerManager()
        self.client = None
        self.workspace_path = None
        self.is_server_running = False
        
    async def start_server(self, workspace_path: str, language: str = "java"):
        """启动语言服务器"""
        workspace_path = os.path.abspath(workspace_path)
        if self.is_server_running and self.workspace_path == workspace_path:
            return
        if self.is_server_running:
            await self.stop_server()
        self.workspace_path = workspace_path
        
        if language == "java":
            reader, writer = await self.server_manager.start_java_server(workspace_path)
        else:
            raise ValueError(f"不支持的语言: {language}")
            
        self.client = LSPClient(reader, writer)
        await self.client.initialize(workspace_path)
        await asyncio.sleep(3)
        
        self.is_server_running = True
    
    async def stop_server(self):
        """停止语言服务器"""
        if not self.is_server_running:
            return
        
        if self.client:
            try:
                await self.client.shutdown()
            except Exception:
                pass
        
        await self.server_manager.stop()
        
        self.is_server_running = False
        self.client = None
        self.workspace_path = None
    
    async def diagnose(
        self,
        project_path: str,
        file_paths: Union[str, List[str]] = None,
        language: str = "java"
    ) -> Dict[str, List[Dict[str, Any]]]:
        """诊断项目中的文件
        
        Args:
            project_path: 项目根目录
            file_paths: 文件路径（可选，不指定则分析所有文件）
                       - 字符串：单个文件
                       - 列表：多个文件
                       - None：自动查找所有文件
            language: 编程语言
            
        Returns:
            字典，key 为文件路径，value 为诊断结果列表
            
        Examples:
            # 分析单个文件
            results = await tool.diagnose("project", "src/Main.java")
            
            # 分析多个文件
            results = await tool.diagnose("project", ["src/Main.java", "src/User.java"])
            
            # 分析整个项目
            results = await tool.diagnose("project")
        """
        try:
            project_path = os.path.abspath(project_path)
            
            # 如果没有指定文件，自动查找所有文件
            if file_paths is None:
                file_paths = self._find_source_files(project_path, language)
                if not file_paths:
                    return {}
            
            # 统一处理：字符串转列表
            if isinstance(file_paths, str):
                file_paths = [file_paths]
            
            # 启动服务器
            await self.start_server(project_path, language)
            
            results = {}
            
            for file_path in file_paths:
                if not os.path.isabs(file_path):
                    abs_file_path = os.path.join(project_path, file_path)
                else:
                    abs_file_path = os.path.abspath(file_path)
                
                if not os.path.exists(abs_file_path):
                    results[file_path] = []
                    continue
                
                try:
                    with open(abs_file_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                except UnicodeDecodeError:
                    try:
                        with open(abs_file_path, 'r', encoding='gbk') as f:
                            code = f.read()
                    except:
                        results[file_path] = []
                        continue
                
                await self.client.open_document(abs_file_path, code, language)
                
                max_wait = 10
                for i in range(max_wait):
                    await asyncio.sleep(1)
                    diagnostics = self.client.get_diagnostics(abs_file_path)
                    if diagnostics:
                        break
                
                diagnostics = self.client.get_diagnostics(abs_file_path)
                results[file_path] = [d.to_dict() for d in diagnostics]
                
                await self.client.close_document(abs_file_path)
            
            return results
        
        finally:
            await self.stop_server()
    
    def _find_source_files(self, project_path: str, language: str) -> List[str]:
        """查找项目中的源文件"""
        extensions = {
            'java': '.java',
            'python': '.py',
            'javascript': '.js',
            'typescript': '.ts'
        }
        
        ext = extensions.get(language, '.java')
        source_files = []
        
        for root, dirs, files in os.walk(project_path):
            # 跳过常见的忽略目录
            dirs[:] = [d for d in dirs if d not in ['.git', 'target', 'build', 'node_modules', '__pycache__']]
            
            for file in files:
                if file.endswith(ext) and not file.startswith('._'):
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, project_path)
                    source_files.append(rel_path)
        
        return source_files
    
    async def __aenter__(self):
        """支持 async with"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出时自动关闭"""
        await self.stop_server()
