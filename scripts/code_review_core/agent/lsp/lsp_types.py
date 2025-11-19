"""LSP 基础类型定义"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Position:
    """文档位置"""
    line: int
    character: int

@dataclass
class Range:
    """文档范围"""
    start: Position
    end: Position

@dataclass
class Diagnostic:
    """诊断信息"""
    range: Range
    severity: int  # 1=Error, 2=Warning, 3=Info, 4=Hint
    message: str
    code: Optional[str] = None
    source: Optional[str] = None
    
    @classmethod
    def from_lsp(cls, data: dict) -> 'Diagnostic':
        """从 LSP 响应创建诊断对象"""
        return cls(
            range=Range(
                start=Position(**data["range"]["start"]),
                end=Position(**data["range"]["end"])
            ),
            severity=data.get("severity", 3),
            message=data["message"],
            code=data.get("code"),
            source=data.get("source")
        )
    
    def to_dict(self) -> dict:
        """转换为字典"""
        severity_map = {1: "Error", 2: "Warning", 3: "Info", 4: "Hint"}
        return {
            "line": self.range.start.line + 1,  # 转换为 1-based
            "character": self.range.start.character,
            "severity": severity_map.get(self.severity, "Unknown"),
            "message": self.message,
            "code": self.code,
            "source": self.source
        }
