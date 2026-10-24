"""库存助手执行器：负责理解请求、编排 Skill 与底层工具调用。"""
import json
import queue
import threading

from helpers import TOOL_SCHEMAS, success, failure, validate_answer
from skill_loader import load_inventory_skill


def _invoke_with_timeout(function, arguments, timeout):
    """以守护线程执行同步工具，超时后让 Agent 立即恢复控制。"""
    result = queue.Queue(maxsize=1)

    def invoke():
        try:
            result.put((True, function(**arguments)))
        except BaseException as exc:
            result.put((False, exc))

    worker = threading.Thread(target=invoke, daemon=True)
    worker.start()
    try:
        succeeded, value = result.get(timeout=timeout)
    except queue.Empty as exc:
        raise TimeoutError(f"MCP 工具调用超过 {timeout} 秒") from exc
    if not succeeded:
        raise value
    return value


def run_agent(request, model, tools, limits):
    model_calls, tool_attempts = 0, 0
    results = []
    try:
        market = request.get("market")
        sku = request.get("sku")
        if not isinstance(market, str) or not market.strip():
            return failure("INVALID_REQUEST", "请求必须包含有效 market", model_calls, tool_attempts)
        if not isinstance(sku, str) or not sku.strip():
            return failure("INVALID_REQUEST", "请求必须包含有效 sku", model_calls, tool_attempts)

        skill = load_inventory_skill()
        messages = [
            {"role": "system", "content": (
                "你是库存查询 Agent。理解用户请求，依据下列 Skill 编排任务并调用工具；"
                "工具负责数据通信，Skill 负责业务规则计算。市场与 SKU 必须始终精确使用请求值，"
                "不得跨市场或跨 SKU 混用数据。工具结果需作为 tool 消息回传，最终仅输出符合 Skill 的 JSON。\n\n"
                f"<inventory_skill>\n{skill}\n</inventory_skill>"
            )},
            {"role": "user", "content": json.dumps(request, ensure_ascii=False)},
        ]
        max_model_calls = max(1, int(limits.get("max_model_calls", 4)))
        max_tool_attempts = max(1, int(limits.get("max_tool_attempts", 6)))
        tool_timeout = float(limits.get("tool_timeout_seconds", 10))
        timeout_retries = max(0, int(limits.get("tool_timeout_retries", 1)))
        if tool_timeout <= 0:
            return failure("INVALID_LIMIT", "tool_timeout_seconds 必须大于 0", model_calls, tool_attempts)

        while model_calls < max_model_calls:
            response = model.next(messages, TOOL_SCHEMAS)
            model_calls += 1
            calls = response.get("tool_calls") or []
            if calls:
                assistant_calls = []
                normalized_calls = []
                for index, call in enumerate(calls):
                    call_id = call.get("id") or f"tool-{model_calls}-{index}"
                    name = call.get("name")
                    arguments = call.get("arguments") or {}
                    if not isinstance(arguments, dict):
                        arguments = json.loads(arguments)
                    if name == "get_metrics":
                        arguments = {**arguments, "market": market, "sku": sku}
                    normalized_calls.append((call_id, name, arguments))
                    assistant_calls.append({
                        "id": call_id,
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)},
                    })
                messages.append({"role": "assistant", "content": response.get("text"), "tool_calls": assistant_calls})

                for call_id, name, arguments in normalized_calls:
                    if name not in tools:
                        return failure("TOOL_ERROR", f"未知工具: {name}", model_calls, tool_attempts)
                    if tool_attempts >= max_tool_attempts:
                        return failure("BUDGET_EXCEEDED", "工具调用额度耗尽", model_calls, tool_attempts)

                    attempts = 0
                    while True:
                        tool_attempts += 1
                        attempts += 1
                        try:
                            value = _invoke_with_timeout(tools[name], arguments, tool_timeout)
                            if name == "get_metrics":
                                if not isinstance(value, dict) or value.get("market") != market or value.get("sku") != sku:
                                    return failure("DATA_ISOLATION_ERROR", "工具返回的市场或 SKU 与请求不一致", model_calls, tool_attempts)
                            results.append({"name": name, "ok": True, "data": value})
                            messages.append({"role": "tool", "tool_call_id": call_id,
                                             "content": json.dumps({"ok": True, "data": value}, ensure_ascii=False)})
                            break
                        except TimeoutError as exc:
                            results.append({"name": name, "ok": False, "error": str(exc)})
                            if attempts > timeout_retries or tool_attempts >= max_tool_attempts:
                                return failure("TOOL_TIMEOUT", str(exc), model_calls, tool_attempts)
                        except Exception as exc:
                            results.append({"name": name, "ok": False, "error": str(exc)})
                            messages.append({"role": "tool", "tool_call_id": call_id,
                                             "content": json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)})
                            break
                continue

            text = response.get("text")
            validation_errors = validate_answer(text, request, results)
            if validation_errors:
                messages.append({"role": "assistant", "content": text})
                messages.append({"role": "user", "content": "请根据 Skill 修正答案。校验问题：" + "；".join(validation_errors)})
                continue
            answer = json.loads(text) if isinstance(text, str) else text
            return success(answer, model_calls, tool_attempts)

        return failure("BUDGET_EXCEEDED", "模型调用额度耗尽", model_calls, tool_attempts)
    except Exception as exc:
        return failure("MODEL_ERROR", str(exc), model_calls, tool_attempts)
