"""LSP 客户端 - 处理与语言服务器的通信"""
import asyncio
import json
from typing import Dict, List, Optional
from pathlib import Path

try:
    from .lsp_types import Diagnostic
except ImportError:
    from .lsp_types import Diagnostic


class LSPClient:
    """LSP 客户端"""
    
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.request_id = 0
        self.pending_requests: Dict[int, asyncio.Future] = {}
        self.diagnostics_cache: Dict[str, List[Diagnostic]] = {}
        self._read_task = None
        
    async def initialize(self, workspace_path: str) -> bool:
        """初始化 LSP 连接"""
        self._read_task = asyncio.create_task(self._read_messages())
        
        workspace_uri = Path(workspace_path).as_uri()
        
        init_params = {
            "processId": None,
            "rootUri": workspace_uri,
            "capabilities": {
                "textDocument": {
                    "publishDiagnostics": {}
                }
            }
        }
        
        response = await self._request("initialize", init_params)
        if response:
            await self._notify("initialized", {})
            return True
        return False
    
    async def open_document(self, file_path: str, content: str, language_id: str = "java") -> None:
        """打开文档"""
        uri = Path(file_path).as_uri()
        await self._notify("textDocument/didOpen", {
            "textDocument": {
                "uri": uri,
                "languageId": language_id,
                "version": 1,
                "text": content
            }
        })
    
    async def close_document(self, file_path: str) -> None:
        """关闭文档"""
        uri = Path(file_path).as_uri()
        await self._notify("textDocument/didClose", {
            "textDocument": {"uri": uri}
        })
    
    def get_diagnostics(self, file_path: str) -> List[Diagnostic]:
        """获取文档的诊断信息"""
        uri = Path(file_path).as_uri()
        
        # 尝试多种 URI 格式匹配
        for cached_uri in self.diagnostics_cache.keys():
            # 直接匹配
            if cached_uri == uri:
                return self.diagnostics_cache[cached_uri]
            
            # 去掉 file:// 前缀后比较路径
            cached_path = cached_uri.replace("file://", "").replace("file:///", "/")
            query_path = uri.replace("file://", "").replace("file:///", "/")
            
            # 解析 URL 编码
            import urllib.parse
            cached_path = urllib.parse.unquote(cached_path)
            query_path = urllib.parse.unquote(query_path)
            
            # 规范化路径后比较
            if Path(cached_path).resolve() == Path(query_path).resolve():
                return self.diagnostics_cache[cached_uri]
        
        return []
    
    async def _request(self, method: str, params: dict) -> Optional[dict]:
        """发送请求并等待响应"""
        self.request_id += 1
        request_id = self.request_id
        
        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }
        
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        await self._send_message(message)
        
        try:
            response = await asyncio.wait_for(future, timeout=30.0)
            return response.get("result")
        except asyncio.TimeoutError:
            return None
        finally:
            self.pending_requests.pop(request_id, None)
    
    async def _notify(self, method: str, params: dict) -> None:
        """发送通知（无需响应）"""
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        await self._send_message(message)
    
    async def _send_message(self, message: dict) -> None:
        """发送消息到 LSP 服务器"""
        content = json.dumps(message).encode('utf-8')
        header = f"Content-Length: {len(content)}\r\n\r\n".encode('utf-8')
        
        self.writer.write(header + content)
        await self.writer.drain()
    
    async def _read_messages(self) -> None:
        """读取来自 LSP 服务器的消息"""
        try:
            while True:
                headers = {}
                while True:
                    line = await self.reader.readline()
                    if not line:
                        return
                    
                    line = line.decode('utf-8').strip()
                    if not line:
                        break
                    
                    if ':' in line:
                        key, value = line.split(':', 1)
                        headers[key.strip()] = value.strip()
                
                if 'Content-Length' not in headers:
                    continue
                
                content_length = int(headers['Content-Length'])
                content = await self.reader.read(content_length)
                
                try:
                    message = json.loads(content.decode('utf-8'))
                    await self._handle_message(message)
                except json.JSONDecodeError:
                    pass
        
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
    
    async def _handle_message(self, message: dict) -> None:
        """处理来自服务器的消息"""
        if "id" in message and message["id"] in self.pending_requests:
            future = self.pending_requests[message["id"]]
            if not future.cancelled():
                future.set_result(message)
        
        elif "method" in message:
            method = message["method"]
            params = message.get("params", {})
            
            if method == "textDocument/publishDiagnostics":
                uri = params.get("uri", "")
                diagnostics_data = params.get("diagnostics", [])
                
                diagnostics = [Diagnostic.from_lsp(d) for d in diagnostics_data]
                self.diagnostics_cache[uri] = diagnostics
    
    async def shutdown(self) -> None:
        """关闭客户端"""
        if self._read_task:
            self._read_task.cancel()
        
        await self._request("shutdown", {})
        await self._notify("exit", {})
