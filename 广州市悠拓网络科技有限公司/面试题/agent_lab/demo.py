import json
import sys
from agent import run_agent
from mcp_client import InventoryTools
from model_client import Model

if __name__ == "__main__":
    request = {"market": sys.argv[1] if len(sys.argv) > 1 else "US", "sku": sys.argv[2] if len(sys.argv) > 2 else "KC01"}
    with InventoryTools() as tools:
        result = run_agent(request, Model(), tools, {"max_model_calls": 4, "max_tool_attempts": 6})
    print(json.dumps(result, ensure_ascii=False, indent=2))
