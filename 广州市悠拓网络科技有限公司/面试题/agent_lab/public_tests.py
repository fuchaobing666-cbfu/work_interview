"""公开测试仅覆盖已声明的三个场景，正式验收使用独立驱动器。"""
import json
from agent import run_agent
ANSWER={"market":"US","sku":"KC01","cover_days":1.08,"risk":"P0","reason":"库存覆盖低于3天"}
class Model:
    def __init__(self,invalid=False): self.calls=0; self.invalid=invalid
    def next(self,messages,schemas):
        self.calls+=1
        returned=[m.get("tool_call_id") for m in messages if m.get("role")=="tool"]
        if self.calls==1: return {"text":None,"tool_calls":[{"id":"metrics-1","name":"get_metrics","arguments":{"market":"US","sku":"KC01"}}]}
        assert "metrics-1" in returned,"工具结果没有正确关联到调用"
        if self.calls==2: return {"text":None,"tool_calls":[{"id":"rule-1","name":"get_risk_rule","arguments":{}}]}
        assert "rule-1" in returned,"缺少风险规则结果"
        if self.invalid and self.calls==3: return {"text":"不是JSON","tool_calls":[]}
        return {"text":json.dumps(ANSWER),"tool_calls":[]}
def case(name,timeout=False,invalid=False):
    attempts=[0]
    def metrics(**kwargs):
        attempts[0]+=1
        if timeout and attempts[0]==1: raise TimeoutError("模拟一次超时")
        return {"market":"US","sku":"KC01","shipped_units":130,"ending_stock":20}
    result=run_agent({"market":"US","sku":"KC01"},Model(invalid),
        {"get_metrics":metrics,"get_risk_rule":lambda:{"p0_below_days":3}},
        {"max_model_calls":4,"max_tool_attempts":6})
    assert result.get("status")=="ok",result
    assert result["answer"]["risk"]=="P0",result
    assert result["usage"]["model_calls"]==(4 if invalid else 3),result
    assert result["usage"]["tool_attempts"]==(3 if timeout else 2),result
    print("PASS",name)
if __name__=="__main__":
    failures=0
    for name,timeout,invalid in [("完整链路",False,False),("超时恢复",True,False),("无效输出修正",False,True)]:
        try: case(name,timeout,invalid)
        except Exception as exc: failures+=1;print("FAIL",name,str(exc))
    print(f"结果：{3-failures}/3 通过")
    raise SystemExit(1 if failures else 0)

