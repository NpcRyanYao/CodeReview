from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Optional

@dataclass
class FunctionSnippet:
    """函数代码片段"""
    id: str
    name: str
    code: str
    file_path: str
    start_line: int
    end_line: int
    language: str
    metadata: Dict[str, Any]

@dataclass
class CodeChange:
    """代码变更信息"""
    file_path: str
    change_type: str  # 'added', 'modified', 'deleted'
    old_content: str
    new_content: str
    line_range: Tuple[int, int]

@dataclass
class SearchResult:
    """搜索结果"""
    function: FunctionSnippet
    similarity_score: float
    vector_distance: float
    match_reason: str

@dataclass
class AnalysisResult:
    """分析结果"""
    analysis_type: str
    duration_ms: float
    similar_functions: List[SearchResult]
    changed_functions: List[FunctionSnippet]
    rebuild_required: bool
    total_files_processed: int
    deleted_functions_count: int = 0

@dataclass
class FunctionProcessingResult:
    """单个函数处理结果"""
    function: FunctionSnippet
    similar_functions: List[SearchResult]
    processing_time_ms: float