from typing import Dict, List, Optional, TypedDict, Annotated, Union
from langchain_core.messages import BaseMessage
from .semantic_analyzer import AnalysisResult
import operator

class CodeReviewState(TypedDict, total=False):
    """
    Central state object maintained throughout the review workflow.
    Uses Annotated types for LangGraph state management.
    """

    # Core workflow data with message accumulation
    messages: Annotated[List[BaseMessage], operator.add]

    # requirements document, code style document
    document: str
    is_document_read: bool

    # Git diff content
    git_diff: str

    # Semantic analysis
    semantic_analysis: Optional[AnalysisResult]
    is_code_retrieved: bool

    # LSP diagnostics
    diagnostics: Optional[Dict]
    project_path: str
    file_paths: Union[None, str, List[str]]
    is_lsp_diagnosed: bool

    # Generated review
    review_comments: Optional[List[Dict]]
    confidence_scores: Optional[Dict]
    review_result: Optional[str]

    # Metadata
    session_id: str
    timestamp: str
    status: str  # "parsing", "retrieving", "analyzing", "complete", "error"

    # Workspace information
    # workspace_id: Optional[str]
    # branch_name: Optional[str]

    # Error handling with accumulation
    errors: Annotated[List[str], operator.add]
    warnings: Annotated[List[str], operator.add]

    # Interactive feedback control
    feedback_loop: bool
    requires_user_input: bool