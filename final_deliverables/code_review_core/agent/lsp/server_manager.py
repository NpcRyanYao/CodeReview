"""语言服务器管理器"""
import asyncio
import os
import tempfile
import shutil
from typing import Optional
from pathlib import Path


class ServerManager:
    """语言服务器进程管理器"""
    
    def __init__(self):
        self.process: Optional[asyncio.subprocess.Process] = None
        self.data_dir: Optional[str] = None
        
    async def start_java_server(self, workspace_path: str) -> tuple:
        """启动 Java 语言服务器
        Returns:
            (reader, writer) 元组
        """
        # 创建临时数据目录
        self.data_dir = tempfile.mkdtemp(prefix="jdtls_")
        
        # 查找 jdtls 安装路径
        jdtls_path = self._find_jdtls()
        if not jdtls_path:
            raise FileNotFoundError(
                "未找到 jdtls。请安装:\n"
                "  macOS: brew install jdtls\n"
                "  或从 https://download.eclipse.org/jdtls/snapshots/ 下载"
            )
        
        # 构建启动命令
        command = self._build_jdtls_command(jdtls_path, self.data_dir)
        
        # 启动进程
        self.process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=workspace_path
        )
        
        return self.process.stdout, self.process.stdin
    
    async def stop(self) -> None:
        """停止语言服务器"""
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
        
        # 清理临时目录
        if self.data_dir and os.path.exists(self.data_dir):
            try:
                shutil.rmtree(self.data_dir)
            except Exception:
                pass
    
    def _find_jdtls(self) -> Optional[str]:
        """查找 jdtls 安装路径"""
        # 首先检查本地目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_jdtls = os.path.join(script_dir, "jdt-language-server-1.52.0-202510301627")
        
        possible_paths = [
            local_jdtls,  # 本地下载的版本
            "/opt/homebrew/opt/jdtls/libexec",
            "/usr/local/opt/jdtls/libexec",
            os.path.expanduser("~/jdtls"),
            os.path.expanduser("~/.local/share/jdtls"),
            "/opt/jdtls",
        ]
        
        for path in possible_paths:
            if os.path.isdir(path):
                launcher_pattern = os.path.join(path, "plugins", "org.eclipse.equinox.launcher_*.jar")
                import glob
                if glob.glob(launcher_pattern):
                    return path
        
        return None
    
    def _build_jdtls_command(self, jdtls_path: str, data_dir: str) -> list:
        """构建 jdtls 启动命令"""
        import glob
        import platform
        
        # 查找 launcher jar
        launcher_pattern = os.path.join(jdtls_path, "plugins", "org.eclipse.equinox.launcher_*.jar")
        launcher_jars = glob.glob(launcher_pattern)
        
        if not launcher_jars:
            raise FileNotFoundError(f"未找到 launcher jar: {launcher_pattern}")
        
        launcher_jar = launcher_jars[0]
        
        # 根据操作系统和架构选择配置目录
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        if system == "darwin":
            # macOS: 检测是 Intel 还是 Apple Silicon
            if machine in ["arm64", "aarch64"]:
                config_dir = "config_mac_arm"
            else:
                config_dir = "config_mac"
        elif system == "linux":
            if machine in ["arm64", "aarch64"]:
                config_dir = "config_linux_arm"
            else:
                config_dir = "config_linux"
        else:
            config_dir = "config_win"
        
        config_path = os.path.join(jdtls_path, config_dir)
        
        # 构建命令
        command = [
            "java",
            "-Declipse.application=org.eclipse.jdt.ls.core.id1",
            "-Dosgi.bundles.defaultStartLevel=4",
            "-Declipse.product=org.eclipse.jdt.ls.core.product",
            "-Dlog.level=ERROR",
            "-Xmx1G",
            "--add-modules=ALL-SYSTEM",
            "--add-opens", "java.base/java.util=ALL-UNNAMED",
            "--add-opens", "java.base/java.lang=ALL-UNNAMED",
            "-jar", launcher_jar,
            "-configuration", config_path,
            "-data", data_dir
        ]
        
        return command
