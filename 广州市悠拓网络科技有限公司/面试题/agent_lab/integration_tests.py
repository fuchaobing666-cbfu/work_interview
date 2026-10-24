"""公开集成检查；正式测试会换市场、商品和运行时 Skill。"""
from mcp_client import InventoryTools
from skill_loader import load_inventory_skill

if __name__ == "__main__":
    skill = load_inventory_skill()
    assert "name: inventory-risk" in skill
    with InventoryTools() as tools:
        assert {"get_metrics", "get_risk_rule"} <= set(tools)
        for market in ("US", "DE"):
            result = tools["get_metrics"](market=market, sku="KC01")
            assert result["market"] == market, result
        try:
            tools["get_metrics"](market="US", sku="MISSING")
        except ValueError:
            pass
        else:
            raise AssertionError("未知商品不应返回其他商品的数据")
    print("PASS MCP 初始化、发现、跨市场调用和未知商品；请再验证 Agent 实际使用 Skill。")
