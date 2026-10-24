# 库存助手交接

同事需要按市场和 SKU 复用这个只读助手，不能串商品、无期限等待或把错误回答当成功。

## 交付约定

入口为 `run_agent(request, model, tools, limits)`。请求含 `market`、`sku`。
返回 `{status, answer, error, usage}`，答案含 `market, sku, cover_days, risk, reason`。
覆盖天数为库存 ÷ 本周发货 × 7；不足 3 天为 P0，其他为 OBSERVE；零发货时天数为 null、等级 UNKNOWN。
一轮最多 4 次模型请求、6 次工具尝试；单个调用超时最多补试一次，业务错误不盲目重试。
额度耗尽返回 `BUDGET_EXCEEDED`，模型故障返回 `MODEL_ERROR`。安全退出必须返回结构化错误。
工具结果格式为 `{role:"tool",tool_call_id,content:JSON字符串}`，内容为 `{ok:true,data:...}` 或 `{ok:false,error:...}`。

`helpers.py` 提供校验器，`model_client.py` 提供考场模型，`mcp_client.py` 提供真实 MCP 客户端。
`mcp_server.py` 是要交接的工具服务，读取 `UFLOW_INVENTORY_PATH`（默认 inventory.json）。
Skill 放在 `skills/inventory-risk/SKILL.md`，遵循带 name、description 的 YAML frontmatter 格式；应说明何时使用、输入输出、步骤及边界。
`skill_loader.py` 从 `UFLOW_SKILL_PATH`（默认上述路径）读取最新 Skill；执行中的 Agent 要实际使用它。
考场已安装官方 Python MCP SDK `mcp==1.26.0`。其他语言可使用同一 MCP stdio 和 JSON 协议。

## 检查与交付

运行 `python3 public_tests.py` 检查公开执行场景；运行 `python3 integration_tests.py` 检查 MCP 和 Skill 接入。
运行 `python3 demo.py US KC01` 完成一次真实模型演示，另可切换市场和 SKU。
留下 `交付说明.md`：修复了什么、实际验证结果、还存在什么限制。正式验收从冻结作品独立运行，不采用本地测试的 PASS 文本作为成绩。

## 跨语言

`submission.json` 可设置 `argv` 数组启动 Agent；`mcp_argv` 数组启动标准 MCP stdio 服务（默认 Python mcp_server.py）。
Agent 进程接收首行 `{"kind":"start","request":...,"limits":...}`。
调用模型输出 `{"kind":"model","messages":[...],"tools":[...]}`，接收 `{ok,response:{text,tool_calls}}`。
调用工具输出 `{"kind":"tool","name":"get_metrics","arguments":{...}}`，接收 `{ok,data}` 或 `{ok:false,error_type,message}`。
最终输出 `{"kind":"result","result":{status,answer,error,usage}}`。每行 flush，日志写 stderr。
正式验收由提供的 MCP 客户端适配器处理工具协议；跨语言代码须读取上述 Skill 与库存数据路径，不能依赖固定样例。
