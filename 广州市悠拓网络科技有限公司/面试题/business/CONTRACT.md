# 现有页面接口

启动：`python business/server.py`，监听 `0.0.0.0:3000`。

页面 `/`；数据 `/metrics.json?market=DE&sku=KC01`。省略筛选参数表示全部。
金额单位人民币，比率是 0—1 数值，未知为 null。现有消费者使用以下字段：

```json
{"current_sales":0,"previous_sales":0,"sales_growth":0,"return_rate":0,"known_ad_spend":0,"ad_spend_missing":0,"ad_rate":null,"rows":[{"market":"US","sku":"KC01","net_sales":0,"sales_growth":0,"ad_rate":null,"return_rate":0,"cover_days":0,"risk":"OBSERVE"}]}
```

rows 的每项对应一个市场与 SKU。保留上述接口，也可更换实现语言。

## 页面交接

页面中的市场选择器 `#market`、SKU 选择器 `#sku` 保留原生 select；空值表示全部。
指标展示保留 `#sales`、`#growth`、`#returns`，明细行保留在 `#rows` 中，数据质量说明保留 `#quality`。
这些标记用于现有页面消费者的交互检查，可调整布局和技术栈。筛选后指标卡与明细应同步更新。
正式验收会实际打开浏览器、切换市场和 SKU，并核对页面显示的指标、商品明细和行动等级；不按页面装饰风格评分。
