"""
State Manager Module - Manages workflow state and enables session persistence
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import copy
import uuid
import json
import logging
from pathlib import Path
from .state import CodeReviewState


logger = logging.getLogger(__name__)


class StateManager:
    """
    Data layer managing state persistence and recovery.
    """
    
    def __init__(self, checkpoint_dir: Optional[str] = None):
        """
        Initialize the state manager.
        
        Args:
            checkpoint_dir: Directory for storing checkpoints (default: temp directory)
        """
        self.current_state: Optional[CodeReviewState] = None
        self.state_history: List[CodeReviewState] = []
        self.checkpoints: Dict[str, CodeReviewState] = {}
        
        # Setup checkpoint directory
        if checkpoint_dir:
            self.checkpoint_dir = Path(checkpoint_dir)
        else:
            self.checkpoint_dir = Path.cwd() / ".checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"StateManager initialized with checkpoint dir: {self.checkpoint_dir}")
        
    def initialize_state(self, initial_data: Dict) -> CodeReviewState:
        """
        Create initial state from input data.
        
        Args:
            initial_data: Dictionary containing initial state data
            
        Returns:
            Initialized CodeReviewState
        """
        from langchain_core.messages import HumanMessage
        
        # Create initial state with all required fields
        self.current_state = {
            "messages": initial_data.get("messages", []),
            "git_diff": initial_data.get("git_diff", ""),
            "ticket_id": initial_data.get("ticket_id"),
            "business_context": None,
            "code_context": None,
            "fast_analysis": None,
            "precise_analysis": None,
            "semantic_analysis": None,
            "diagnostics": None,
            "references": None,
            "review_comments": None,
            "confidence_scores": None,
            "review_result": None,
            "session_id": initial_data.get("session_id", str(uuid.uuid4())),
            "timestamp": datetime.now().isoformat(),
            "status": "parsing",
            "workspace_id": initial_data.get("workspace_id"),
            "branch_name": initial_data.get("branch_name"),
            "errors": [],
            "warnings": [],
            "feedback_loop": False,
            "requires_user_input": False
        }
        
        # Add to history
        self.state_history.append(copy.deepcopy(self.current_state))
        
        logger.info(f"State initialized with session_id: {self.current_state['session_id']}")
        return self.current_state
        
    def update_state(self, updates: Dict) -> CodeReviewState:
        """
        Apply updates to current state.
        
        Args:
            updates: Dictionary of updates to apply
            
        Returns:
            Updated state
        """
        if not self.current_state:
            raise RuntimeError("State not initialized. Call initialize_state first.")
            
        # Apply updates
        for key, value in updates.items():
            if key in self.current_state:
                # Special handling for list fields with operator.add annotation
                if key in ["messages", "errors", "warnings"] and isinstance(value, list):
                    # Append to existing list
                    self.current_state[key].extend(value)
                else:
                    # Direct replacement for other fields
                    self.current_state[key] = value
                logger.debug(f"Updated state field '{key}'")
                
        # Update timestamp
        self.current_state["timestamp"] = datetime.now().isoformat()
        
        # Add to history
        self.state_history.append(copy.deepcopy(self.current_state))
        
        return self.current_state
        
    def create_checkpoint(self, checkpoint_id: str) -> None:
        """
        Create a restorable checkpoint.
        
        Args:
            checkpoint_id: Unique identifier for the checkpoint
        """
        if not self.current_state:
            raise RuntimeError("Cannot create checkpoint: no current state")
            
        # Store in memory
        self.checkpoints[checkpoint_id] = copy.deepcopy(self.current_state)
        
        # Also persist to disk
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        with open(checkpoint_file, "w") as f:
            # Convert non-serializable objects for JSON
            state_dict = self._prepare_for_serialization(self.current_state)
            json.dump(state_dict, f, indent=2)
            
        logger.info(f"Created checkpoint: {checkpoint_id}")
            
    def restore_checkpoint(self, checkpoint_id: str) -> Optional[CodeReviewState]:
        """
        Restore state from checkpoint.
        
        Args:
            checkpoint_id: Checkpoint identifier to restore
            
        Returns:
            Restored state or None if checkpoint not found
        """
        # Try memory first
        if checkpoint_id in self.checkpoints:
            self.current_state = copy.deepcopy(self.checkpoints[checkpoint_id])
            logger.info(f"Restored checkpoint from memory: {checkpoint_id}")
            return self.current_state
            
        # Try disk
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        if checkpoint_file.exists():
            with open(checkpoint_file, "r") as f:
                state_dict = json.load(f)
                self.current_state = self._restore_from_serialization(state_dict)
                # Cache in memory
                self.checkpoints[checkpoint_id] = copy.deepcopy(self.current_state)
                logger.info(f"Restored checkpoint from disk: {checkpoint_id}")
                return self.current_state
                
        logger.warning(f"Checkpoint not found: {checkpoint_id}")
        return None
        
    def get_state_history(self, limit: int = 10) -> List[CodeReviewState]:
        """
        Get recent state history.
        
        Args:
            limit: Maximum number of states to return
            
        Returns:
            List of recent states
        """
        return self.state_history[-limit:]
        
    def clear_history(self) -> None:
        """Clear state history to free memory."""
        self.state_history = []
        if self.current_state:
            self.state_history.append(copy.deepcopy(self.current_state))
        logger.info("State history cleared")
        
    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current state.
        
        Returns:
            Dictionary containing state summary
        """
        if not self.current_state:
            return {"status": "not_initialized"}
            
        return {
            "session_id": self.current_state.get("session_id"),
            "status": self.current_state.get("status"),
            "timestamp": self.current_state.get("timestamp"),
            "message_count": len(self.current_state.get("messages", [])),
            "error_count": len(self.current_state.get("errors", [])),
            "warning_count": len(self.current_state.get("warnings", [])),
            "has_business_context": bool(self.current_state.get("business_context")),
            "has_code_context": bool(self.current_state.get("code_context")),
            "has_review": bool(self.current_state.get("review_result")),
            "checkpoint_count": len(self.checkpoints),
            "history_length": len(self.state_history)
        }
        
    def _prepare_for_serialization(self, state: CodeReviewState) -> Dict:
        """
        Prepare state for JSON serialization.
        
        Args:
            state: State to prepare
            
        Returns:
            JSON-serializable dictionary
        """
        # Convert messages to simple dictionaries
        serializable = copy.deepcopy(state)
        if "messages" in serializable:
            serializable["messages"] = [
                {"type": msg.__class__.__name__, "content": msg.content}
                for msg in serializable["messages"]
            ]
        return serializable
        
    def _restore_from_serialization(self, state_dict: Dict) -> CodeReviewState:
        """
        Restore state from JSON-serialized dictionary.
        
        Args:
            state_dict: Serialized state dictionary
            
        Returns:
            Restored CodeReviewState
        """
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
        
        # Restore messages
        if "messages" in state_dict:
            message_classes = {
                "HumanMessage": HumanMessage,
                "SystemMessage": SystemMessage,
                "AIMessage": AIMessage
            }
            state_dict["messages"] = [
                message_classes.get(msg["type"], HumanMessage)(content=msg["content"])
                for msg in state_dict["messages"]
            ]
        return state_dict
        
    def export_state(self, file_path: str) -> None:
        """
        Export current state to a file.
        
        Args:
            file_path: Path to export file
        """
        if not self.current_state:
            raise RuntimeError("No state to export")
            
        state_dict = self._prepare_for_serialization(self.current_state)
        with open(file_path, "w") as f:
            json.dump(state_dict, f, indent=2)
        logger.info(f"State exported to: {file_path}")
        
    def import_state(self, file_path: str) -> CodeReviewState:
        """
        Import state from a file.
        
        Args:
            file_path: Path to import file
            
        Returns:
            Imported state
        """
        with open(file_path, "r") as f:
            state_dict = json.load(f)
        self.current_state = self._restore_from_serialization(state_dict)
        self.state_history.append(copy.deepcopy(self.current_state))
        logger.info(f"State imported from: {file_path}")
        return self.current_state