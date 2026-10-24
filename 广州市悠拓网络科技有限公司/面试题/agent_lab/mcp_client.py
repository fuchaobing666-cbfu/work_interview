"""同步 MCP 适配器；每次请求独立会话并受环境配置的时限约束。"""
import asyncio
import json
import os
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class InventoryTools:
    def _timeout_seconds(self):
        try:
            timeout = float(os.environ.get("UFLOW_MCP_TIMEOUT_SECONDS", "10"))
        except ValueError as exc:
            raise ValueError("UFLOW_MCP_TIMEOUT_SECONDS 必须为正数") from exc
        if timeout <= 0:
            raise ValueError("UFLOW_MCP_TIMEOUT_SECONDS 必须为正数")
        return timeout

    def _run_request(self, name=None, arguments=None):
        timeout = self._timeout_seconds()
        try:
            return asyncio.run(asyncio.wait_for(self._request(name, arguments), timeout=timeout))
        except asyncio.TimeoutError as exc:
            operation = "工具发现" if name is None else f"工具 {name}"
            raise TimeoutError(f"MCP {operation}超过 {timeout:g} 秒") from exc

    async def _request(self, name=None, arguments=None):
        server = StdioServerParameters(command=sys.executable,
            args=[str(Path(__file__).parent / "mcp_server.py")], env=dict(os.environ))
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                if name is None:
                    return [tool.name for tool in (await session.list_tools()).tools]
                result = await session.call_tool(name, arguments or {})
        if result.isError:
            details = "; ".join(item.text for item in result.content if hasattr(item, "text"))
            raise ValueError(details or f"MCP 工具调用失败: {name}")
        if result.structuredContent is not None:
            return result.structuredContent
        return json.loads(next(item.text for item in result.content if hasattr(item, "text")))

    def __enter__(self):
        return {name: self._tool(name) for name in self._run_request()}

    def _tool(self, name):
        def call(**arguments):
            return self._run_request(name, arguments)
        return call

    def __exit__(self, *args):
        pass
