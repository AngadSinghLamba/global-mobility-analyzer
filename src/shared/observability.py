import logging
from typing import Any, Dict, Optional
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

# Initialize logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Rough estimate prices for Gemini 1.5 Pro to serve as placeholders
# Input: $1.25 / 1M tokens, Output: $5.00 / 1M tokens
GEMINI_PRICING = {
    "input_cost_per_1k": 0.00125,
    "output_cost_per_1k": 0.005
}

class TokenTracker(BaseCallbackHandler):
    """
    Custom callback handler to track token usage across the LangGraph execution.
    Logs input/output/total tokens per node and calculates estimated cost.
    """
    def __init__(self):
        self.node_usage: Dict[str, Dict[str, Any]] = {}
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: list[str], **kwargs: Any
    ) -> Any:
        pass

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        """Track tokens when LLM call completes."""
        node_name = kwargs.get("tags", ["default"])[0] if kwargs.get("tags") else "unknown_node"
        
        if response.llm_output and "token_usage" in response.llm_output:
            usage = response.llm_output["token_usage"]
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            
            # Update global counts
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            
            # Calculate cost
            cost = (input_tokens / 1000 * GEMINI_PRICING["input_cost_per_1k"]) + \
                   (output_tokens / 1000 * GEMINI_PRICING["output_cost_per_1k"])
            self.total_cost_usd += cost
            
            # Update node stats
            if node_name not in self.node_usage:
                self.node_usage[node_name] = {"input": 0, "output": 0, "cost": 0.0}
            
            self.node_usage[node_name]["input"] += input_tokens
            self.node_usage[node_name]["output"] += output_tokens
            self.node_usage[node_name]["cost"] += cost
            
            logger.info(f"LLM Call [{node_name}] - Tokens: {input_tokens} in / {output_tokens} out. Cost: ${cost:.6f}")

    def get_summary(self) -> Dict[str, Any]:
        """Return a dictionary summarizing the run's token usage."""
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": self.total_cost_usd,
            "node_breakdown": self.node_usage
        }

    def print_summary(self):
        """Print a formatted summary to the console."""
        print("\n" + "="*40)
        print("📊 TOKEN USAGE & COST REPORT")
        print("="*40)
        print(f"Total Input Tokens:  {self.total_input_tokens:,}")
        print(f"Total Output Tokens: {self.total_output_tokens:,}")
        print(f"Estimated Cost:      ${self.total_cost_usd:.6f}")
        print("-" * 40)
        for node, data in self.node_usage.items():
            print(f"Node [{node}]:")
            print(f"  - In:  {data['input']:,}")
            print(f"  - Out: {data['output']:,}")
            print(f"  - USD: ${data['cost']:.6f}")
        print("="*40 + "\n")
