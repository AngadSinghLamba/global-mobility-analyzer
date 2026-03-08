from typing import Dict, Any, List, Optional, Annotated
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
import operator

def merge_token_usage(left: dict, right: dict) -> dict:
    """Merges two token usage dictionaries."""
    if not left:
        return right
    if not right:
        return left
    
    merged = left.copy()
    for k, v in right.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            for sub_k, sub_v in v.items():
                merged[k][sub_k] = merged[k].get(sub_k, 0) + sub_v
        else:
            merged[k] = merged.get(k, 0) + v
    return merged

class GraphState(TypedDict):
    """
    Main state for the Global Mobility Analyzer subgraph.
    """
    # Applicant input
    profile: Dict[str, Any]
    target_country: str
    
    # Processing state
    current_query: str
    retrieved_documents: List[Dict[str, Any]]
    contradictory_chunks: List[str]
    retries: int
    
    # Final output
    assessment: Optional[Dict[str, Any]]
    
    # Observability
    token_usage: Annotated[Dict[str, Any], merge_token_usage]
