# context_manager.py
"""
Intelligent Context Window Management with Relevance Scoring
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import json
import hashlib
from datetime import datetime


@dataclass
class ContextItem:
    """Single piece of context"""
    id: str
    content: Any
    type: str  # "observation", "reflection", "tool_result", "user_query"
    timestamp: float
    relevance_score: float = 0.0
    embeddings: Optional[List[float]] = None  # For future semantic search
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "type": self.type,
            "timestamp": self.timestamp,
            "relevance_score": self.relevance_score
        }


class RelevanceScorer:
    """Scores context items by relevance to current query"""
    
    def __init__(self, llm):
        self.llm = llm
    
    def score_batch(self, items: List[ContextItem], current_query: str) -> List[ContextItem]:
        """
        Score multiple context items for relevance
        
        Uses LLM to determine which past context is relevant
        """
        
        # Simple keyword-based scoring for now
        # TODO: Upgrade to semantic similarity with embeddings
        
        query_keywords = set(current_query.lower().split())
        
        for item in items:
            content_str = str(item.content).lower()
            content_keywords = set(content_str.split())
            
            # Jaccard similarity
            intersection = query_keywords & content_keywords
            union = query_keywords | content_keywords
            
            if union:
                item.relevance_score = len(intersection) / len(union)
            else:
                item.relevance_score = 0.0
            
            # Boost recent items
            import time
            age_hours = (time.time() - item.timestamp) / 3600
            recency_boost = max(0, 1.0 - (age_hours / 24))  # Decay over 24 hours
            
            item.relevance_score = (item.relevance_score * 0.7) + (recency_boost * 0.3)
        
        return sorted(items, key=lambda x: x.relevance_score, reverse=True)


class ContextCompressor:
    """Compress context to fit in token limits"""
    
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
    
    def compress(self, items: List[ContextItem]) -> str:
        """
        Compress context items into a summary
        
        Strategy:
        1. Keep high-relevance items in full
        2. Summarize medium-relevance items
        3. Drop low-relevance items
        """
        
        high_relevance = [item for item in items if item.relevance_score > 0.7]
        medium_relevance = [item for item in items if 0.3 <= item.relevance_score <= 0.7]
        
        # Build compressed context
        compressed_parts = []
        
        # Full details for high relevance
        if high_relevance:
            compressed_parts.append("=== HIGH RELEVANCE CONTEXT ===")
            for item in high_relevance[:5]:  # Top 5
                compressed_parts.append(f"{item.type}: {item.content}")
        
        # Summaries for medium relevance
        if medium_relevance:
            compressed_parts.append("\n=== RELATED CONTEXT ===")
            summaries = [f"- {item.type}" for item in medium_relevance[:3]]
            compressed_parts.extend(summaries)
        
        return "\n".join(compressed_parts)


class SessionStateManager:
    """Manages session state with persistence and replay"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.checkpoint_dir = "session_checkpoints"
        self.context_items: List[ContextItem] = []
        self.checkpoints: List[Dict[str, Any]] = []
        
        import os
        os.makedirs(self.checkpoint_dir, exist_ok=True)
    
    def add_context(self, content: Any, context_type: str) -> None:
        """Add new context item"""
        import time
        
        item_id = hashlib.md5(
            f"{time.time()}{context_type}{content}".encode()
        ).hexdigest()[:8]
        
        item = ContextItem(
            id=item_id,
            content=content,
            type=context_type,
            timestamp=time.time()
        )
        
        self.context_items.append(item)
    
    def save_checkpoint(self, name: str) -> str:
        """Save current session state as checkpoint"""
        import time
        
        checkpoint = {
            "name": name,
            "timestamp": time.time(),
            "session_id": self.session_id,
            "context_items": [item.to_dict() for item in self.context_items],
            "item_count": len(self.context_items)
        }
        
        self.checkpoints.append(checkpoint)
        
        # Save to disk
        checkpoint_file = f"{self.checkpoint_dir}/{self.session_id}_{name}.json"
        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint, f, indent=2)
        
        print(f"✓ Checkpoint saved: {checkpoint_file}")
        return checkpoint_file
    
    def restore_checkpoint(self, name: str) -> bool:
        """Restore session from checkpoint"""
        checkpoint_file = f"{self.checkpoint_dir}/{self.session_id}_{name}.json"
        
        try:
            with open(checkpoint_file, "r") as f:
                checkpoint = json.load(f)
            
            # Restore context items
            self.context_items = [
                ContextItem(**item_data)
                for item_data in checkpoint["context_items"]
            ]
            
            print(f"✓ Restored {len(self.context_items)} context items from checkpoint")
            return True
            
        except Exception as e:
            print(f"❌ Failed to restore checkpoint: {e}")
            return False
    
    def fork_session(self, new_session_id: str) -> 'SessionStateManager':
        """Create a new session branching from current state"""
        new_session = SessionStateManager(new_session_id)
        new_session.context_items = self.context_items.copy()
        
        print(f"✓ Forked session: {new_session_id}")
        return new_session
    
    def replay_session(self) -> List[Dict[str, Any]]:
        """Get session history for replay/debugging"""
        return [item.to_dict() for item in self.context_items]
    
    def prune_by_relevance(self, current_query: str, llm, keep_top_n: int = 20) -> None:
        """Remove low-relevance context to save memory"""
        scorer = RelevanceScorer(llm)
        scored_items = scorer.score_batch(self.context_items, current_query)
        
        # Keep only top N
        self.context_items = scored_items[:keep_top_n]
        
        print(f"✓ Pruned context to top {keep_top_n} items")