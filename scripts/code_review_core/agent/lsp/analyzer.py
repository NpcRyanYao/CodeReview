#!/usr/bin/env python3
"""代码分析工具"""
import asyncio
import json
import os
import sys
from datetime import datetime

from .diagnostic_tool_final import CodeDiagnosticTool


class CodeAnalyzer:
    """代码分析工具"""
    
    def __init__(self):
        self.tool = CodeDiagnosticTool()
        self.results = []
    
    async def analyze(self, project_path: str, file_paths=None):
        """分析项目
        Args:
            project_path: 项目路径
            file_paths: 文件路径列表（可选，None 表示分析整个项目）
        """
        res = {}
        results_dict = await self.tool.diagnose(project_path, file_paths)
        
        if not results_dict:
            # print("未找到文件或没有问题")
            # res.update({file_paths : "File not found or no issues."})
            return None
        
        total_issues = sum(len(diags) for diags in results_dict.values())
        
        result = {
            "project_path": project_path,
            "timestamp": datetime.now().isoformat(),
            "files": results_dict,
            "total_files": len(results_dict),
            "total_issues": total_issues
        }
        
        self.results.append(result)

        for file_path, diagnostics in results_dict.items():
            res.update(self._return_diagnostics(file_path, diagnostics))

        return res


    def _return_diagnostics(self, file_path: str, diagnostics: list):
        str1 =[]
        
        """保存诊断结果"""
        # print(f"\n{file_path}")
        
        if not diagnostics:
            # print("  ✓ 没有发现问题")
            str1 = [" ✓ No problems were found."]
            print(str1)
        else:
            
            # print(f"  发现 {len(diagnostics)} gege个问题:")
            str2 = f"found {len(diagnostics)} issue(s):"
            str1 = [str2]
            for diag in diagnostics:
                severity = diag['severity']
                line = diag['line']
                message = diag['message']
                
                symbol = {
                    'Error': '✗',
                    'Warning': '⚠',
                    'Info': 'ℹ',
                    'Hint': '💡'
                }.get(severity, '•')
                
                # print(f"    {symbol} [{severity}] 第 {line} 行: {message}")
                str2 = f"{symbol} [{severity}] line {line} : {message}"
                str1.append(str2)
        resdic = {
            file_path:str1
        }
        return resdic


async def toolcx(project_path: str, file_paths=None):
    """主函数
    
    Args:
        project_path: 项目路径
        file_paths: 文件路径（可选）
    """
    analyzer = CodeAnalyzer()
    dicx = await analyzer.analyze(project_path, file_paths)
    # analyzer.save_results()
    return dicx


def parse_args():
    """解析命令行参数"""
    if len(sys.argv) < 2:
        # print("用法:")
        # print("  分析整个项目: python3 analyzer.py <项目路径>")
        # print("  分析指定文件: python3 analyzer.py <项目路径> <文件1> [文件2] [文件3] ...")
        # print("\n示例:")
        # print("  python3 analyzer.py ./my-project")
        # print("  python3 analyzer.py ./my-project src/Main.java")
        # print("  python3 analyzer.py ./my-project src/Main.java src/User.java")
        sys.exit(1)
    
    project_path = sys.argv[1]
    
    # 如果有文件参数，统一返回列表；否则返回 None（分析整个项目）
    file_paths = sys.argv[2:] if len(sys.argv) > 2 else None
    
    return project_path, file_paths