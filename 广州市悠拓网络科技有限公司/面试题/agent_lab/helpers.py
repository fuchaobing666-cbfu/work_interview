import json, math
TOOL_SCHEMAS=[
 {"type":"function","function":{"name":"get_metrics","description":"查询指定市场和SKU的本周发货件数与期末库存","parameters":{"type":"object","properties":{"market":{"type":"string"},"sku":{"type":"string"}},"required":["market","sku"]}}},
 {"type":"function","function":{"name":"get_risk_rule","description":"取得库存风险阈值","parameters":{"type":"object","properties":{}}}}
]
def success(answer,model_calls,tool_attempts):
    return {"status":"ok","answer":answer,"error":None,"usage":{"model_calls":model_calls,"tool_attempts":tool_attempts}}
def failure(code,message,model_calls,tool_attempts):
    return {"status":"error","answer":None,"error":{"code":code,"message":message},"usage":{"model_calls":model_calls,"tool_attempts":tool_attempts}}
def validate_answer(text, request, results):
    try: answer=json.loads(text) if isinstance(text,str) else text
    except (ValueError,TypeError): return ["答案不是有效JSON"]
    if not isinstance(answer,dict): return ["答案必须为对象"]
    errors=[]
    metrics=next((r.get("data") for r in reversed(results) if r.get("name")=="get_metrics" and r.get("ok")),None)
    rule=next((r.get("data") for r in reversed(results) if r.get("name")=="get_risk_rule" and r.get("ok")),None)
    if not metrics or not rule: return ["缺少本次成功的工具证据"]
    if answer.get("market")!=request["market"] or answer.get("sku")!=request["sku"]: errors.append("市场或SKU与请求不一致")
    cover=metrics["ending_stock"]/metrics["shipped_units"]*7 if metrics["shipped_units"] else None
    risk="UNKNOWN" if cover is None else ("P0" if cover<rule["p0_below_days"] else "OBSERVE")
    if cover is None:
        if answer.get("cover_days") is not None: errors.append("零发货时覆盖天数必须null")
    elif not isinstance(answer.get("cover_days"),(float,int)) or not math.isfinite(answer["cover_days"]) or abs(answer["cover_days"]-cover)>0.015:
        errors.append("覆盖天数与工具证据不符")
    if answer.get("risk")!=risk: errors.append("风险等级不正确")
    if not isinstance(answer.get("reason"),str) or not answer["reason"].strip(): errors.append("缺少判断理由")
    return errors

