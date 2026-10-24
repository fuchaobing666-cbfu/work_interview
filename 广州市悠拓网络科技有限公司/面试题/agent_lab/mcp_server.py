"""库存数据 MCP 适配器；只读取并隔离数据，不计算库存风险。stdout 专用于 MCP 协议。"""
import json
import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("inventory-tools")


def _load_inventory():
    source = Path(os.environ.get("UFLOW_INVENTORY_PATH", Path(__file__).parent / "inventory.json"))
    return json.loads(source.read_text(encoding="utf-8"))


@mcp.tool()
def get_metrics(market: str, sku: str) -> dict:
    """精确查询市场和 SKU 对应的原始库存指标；不做业务计算。"""
    if not isinstance(market, str) or not market.strip():
        raise ValueError("市场参数不能为空")
    if not isinstance(sku, str) or not sku.strip():
        raise ValueError("SKU 参数不能为空")

    matches = [row for row in _load_inventory()
               if row.get("market") == market and row.get("sku") == sku]
    if not matches:
        raise ValueError(f"商品不存在: market={market}, sku={sku}")
    if len(matches) > 1:
        raise ValueError(f"库存数据存在重复记录: market={market}, sku={sku}")
    return matches[0]


@mcp.tool()
def get_risk_rule() -> dict:
    """提供兼容用的阈值配置数据；风险计算和分级由 Skill 负责。"""
    return {"p0_below_days": 3}


if __name__ == "__main__":
    mcp.run(transport="stdio")
