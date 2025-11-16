"""
Agent core engine

LangGraph workflow management
"""
import asyncio
from typing import Dict, Any, Optional, Literal
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph

from .state import CodeReviewState


class AgentCore:
    """Agent core engine"""
    
    def __init__(self):
        # self.state_manager = StateManager()
        self.graph = self._build_workflow()

    def _build_workflow(self) -> CompiledStateGraph:
        """generate LangGraph workflow"""
        
        workflow = StateGraph(state_schema=CodeReviewState)
        
        # add node
        workflow.add_node("start", self._start)
        workflow.add_node("read_document_content", self._read_document_content)
        workflow.add_node("retrieval_vector_database", self._retrieval_vector_database)
        workflow.add_node("lsp_diagnostics", self._lsp_diagnostics)
        workflow.add_node("llm_diagnostics", self._llm_diagnostics)
        workflow.add_node("display_on_github", self._display_on_github)

        
        # add edge
        workflow.set_entry_point("start")
        workflow.add_edge("start", "read_document_content")
        workflow.add_edge("start", "lsp_diagnostics")
        workflow.add_edge("start", "retrieval_vector_database")

        # conditional edge from read document node to llm node or read document node
        workflow.add_conditional_edges(
            "read_document_content",  # 源节点是“生成文档”，判断逻辑在 condition 里
            self._read_document_to_llm_condition,
            {
                "llm_diagnostics": "llm_diagnostics",
                "read_document_content": "read_document_content"
            }
        )

        # conditional edge from retrieval vector database node to llm node or retrieval vector database node
        workflow.add_conditional_edges(
            "retrieval_vector_database",
            self._retrieval_database_to_llm_condition,
            {
                "retrieval_vector_database": "retrieval_vector_database",
                "llm_diagnostics": "llm_diagnostics"
            }
        )

        workflow.add_conditional_edges(
            "lsp_diagnostics",
            self._lsp_diagnostics_to_llm_condition,
            {
                "lsp_diagnostics": "lsp_diagnostics",
                "llm_diagnostics": "llm_diagnostics"
            }
        )

        workflow.add_conditional_edges(
            "llm_diagnostics",
            self._llm_to_other_node,
            {
                "read_document_content": "read_document_content",
                "lsp_diagnostics": "lsp_diagnostics",
                "retrieval_vector_database": "retrieval_vector_database",
                "display_on_github": "display_on_github"
            }
        )

        workflow.add_edge("display_on_github", END)
        
        return workflow.compile()

    async def _start(self, state: CodeReviewState) -> CodeReviewState:
        print("start")
        await asyncio.sleep(3)
        return {}

    async def _read_document_content(self, state: CodeReviewState) -> CodeReviewState:
        print("_read_document_content executing")
        await asyncio.sleep(3)
        print("_read_document_content finished")
        return {"is_document_read": True}
    
    async def _retrieval_vector_database(self, state: CodeReviewState) -> CodeReviewState:
        print("_retrieval_vector_database executing")
        await asyncio.sleep(3)
        print("_retrieval_vector_database finished")
        return {"is_code_retrieved": True}
    
    async def _lsp_diagnostics(self, state: CodeReviewState) -> CodeReviewState:
        print("_lsp_diagnostics executing")
        await asyncio.sleep(3)
        print("_lsp_diagnostics finished")
        return {"is_lsp_diagnosed": True}
    
    async def _llm_diagnostics(self, state: CodeReviewState) -> CodeReviewState:
        print("_llm_diagnostics executing")
        await asyncio.sleep(3)
        print("_llm_diagnostics finished")
        return {}
    
    async def _display_on_github(self, state: CodeReviewState) -> CodeReviewState:
        print("_display_on_github executing")
        await asyncio.sleep(3)
        print("_display_on_github finished")
        return {}

    def _read_document_to_llm_condition(self, state: CodeReviewState) -> Literal["read_document_content", "llm_diagnostics"]:
        """conditional edge from read document node to llm node"""
        if state["is_document_read"]:
            return "llm_diagnostics"
        else:
            return "read_document_content"

    def _retrieval_database_to_llm_condition(self, state: CodeReviewState) -> Literal["retrieval_vector_database", "llm_diagnostics"]:
        """conditional edge from retrieval database node to llm node"""
        if state["is_code_retrieved"]:
            return "llm_diagnostics"
        else:
            return "retrieval_vector_database"

    def _lsp_diagnostics_to_llm_condition(self, state: CodeReviewState) -> Literal["lsp_diagnostics", "llm_diagnostics"]:
        """conditional edge from lsp diagnostics node to llm node"""
        if state["is_lsp_diagnosed"]:
            return "llm_diagnostics"
        else:
            return "lsp_diagnostics"

    def _llm_to_other_node(self, state: CodeReviewState) -> Literal["lsp_diagnostics", "retrieval_vector_database", "read_document_content", "display_on_github"]:
        if not state["is_document_read"]:
            return "read_document_content"
        elif not state["is_lsp_diagnosed"]:
            return "lsp_diagnostics"
        elif not state["is_code_retrieved"]:
            return "retrieval_vector_database"
        else:
            return "display_on_github"

    async def review_code(self, git_diff: str) -> Dict[str, Any]:
        """Execute code review"""
        initial_state: CodeReviewState = {
            "messages": [HumanMessage(content=f"Review this code change: {git_diff[:500]}...")],
            "git_diff": git_diff,
            "code_context": None,
            "review_result": None,
            "feedback_loop": False,
            "is_document_read": False,
            "is_code_retrieved": False,
            "is_lsp_diagnosed": False,
            "errors": [],
            "warnings": []
        }
        # execute workflow
        final_state = await self.graph.ainvoke(initial_state)
        
        return final_state