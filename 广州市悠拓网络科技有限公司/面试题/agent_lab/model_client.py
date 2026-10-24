import json, os
from urllib.request import Request, urlopen
class Model:
    def next(self,messages,tool_schemas):
        url=os.environ.get("UFLOW_LAB_BASE_URL")
        token=os.environ.get("UFLOW_LAB_TOKEN")
        if not url or not token: raise RuntimeError("考场模型代理未配置，请联系监考人员")
        req=Request(url,data=json.dumps({"messages":messages,"tools":tool_schemas}).encode(),
            headers={"Content-Type":"application/json","Authorization":"Bearer "+token})
        with urlopen(req,timeout=90) as response:
            data=json.load(response)
        return data.get("data",data)

