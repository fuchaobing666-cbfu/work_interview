"""经营页面数据接口：按市场和 SKU 汇总销售、库存及退货风险。"""
import csv
from collections import defaultdict
from pathlib import Path

# 退货率较前周增长达到 50% 时，视为异常上涨。
RETURN_GROWTH_ALERT = 0.5
STOCKOUT_DAYS = 3


def load_rows():
    with (Path(__file__).parent / "sales.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _number(value):
    if value is None or value == "":
        return None
    return float(value)


def _deduplicate(rows):
    """同一业务记录只计一次；没有 record_id 的行仍保留。"""
    seen = set()
    unique = []
    for row in rows:
        record_id = row.get("record_id")
        if record_id and record_id in seen:
            continue
        if record_id:
            seen.add(record_id)
        unique.append(row)
    return unique


def _sum(rows, field):
    return sum((_number(row.get(field)) or 0) for row in rows)


def _rate(numerator, denominator):
    return numerator / denominator if denominator else None


def build_metrics(market=None, sku=None):
    rows = _deduplicate(load_rows())
    if market:
        rows = [row for row in rows if row["market"] == market]
    if sku:
        rows = [row for row in rows if row["sku"] == sku]

    weeks = sorted({row["week_end"] for row in rows})
    current_week = weeks[-1] if weeks else None
    previous_week = weeks[-2] if len(weeks) > 1 else None
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["market"], row["sku"])].append(row)

    output_rows = []
    for (row_market, row_sku), group in sorted(grouped.items()):
        current = [row for row in group if row["week_end"] == current_week]
        previous = [row for row in group if row["week_end"] == previous_week]
        current_sales = _sum(current, "net_sales")
        previous_sales = _sum(previous, "net_sales")
        current_shipped = _sum(current, "shipped_units")
        previous_shipped = _sum(previous, "shipped_units")
        current_returns = _sum(current, "returned_units")
        previous_returns = _sum(previous, "returned_units")
        current_return_rate = _rate(current_returns, current_shipped)
        previous_return_rate = _rate(previous_returns, previous_shipped)
        if previous_return_rate is None:
            return_growth = None
        elif previous_return_rate == 0:
            return_growth = 0 if current_return_rate == 0 else None
        else:
            return_growth = (current_return_rate - previous_return_rate) / previous_return_rate

        # 库存是时点数量，不跨记录相加；取当前周最后一条记录的周末库存。
        current_stock = _number(current[-1].get("ending_stock")) if current else None
        cover_days = (
            current_stock / (current_shipped / 7)
            if current_stock is not None and current_shipped > 0
            else None
        )
        current_ad_spend = [_number(row.get("ad_spend")) for row in current]
        known_ad_spend = sum(value for value in current_ad_spend if value is not None)
        ad_rate = _rate(known_ad_spend, current_sales)
        sales_growth = (
            (current_sales - previous_sales) / previous_sales
            if previous_sales else None
        )

        risk_types = []
        reasons = []
        if cover_days is not None and cover_days < STOCKOUT_DAYS:
            risk_types.append("断货预警")
            reasons.append(f"库存仅可覆盖 {cover_days:.2f} 天，低于 {STOCKOUT_DAYS} 天预警线")
        rising_return = return_growth is not None and return_growth >= RETURN_GROWTH_ALERT
        high_and_rising = (
            current_return_rate is not None
            and current_return_rate >= 0.10
            and (previous_return_rate is None or current_return_rate > previous_return_rate)
        )
        if rising_return or high_and_rising:
            risk_types.append("退货异常上涨")
            if rising_return:
                reasons.append(
                    f"退货率环比增长 {return_growth:.2%}，达到 {RETURN_GROWTH_ALERT:.0%} 预警线"
                )
            else:
                reasons.append(f"退货率升至 {current_return_rate:.2%}，达到 10% 且较前周上升")

        risk = "P0" if "断货预警" in risk_types else "P1" if risk_types else "OBSERVE"
        output_rows.append({
            "market": row_market,
            "sku": row_sku,
            "net_sales": current_sales,
            "sales_growth": sales_growth,
            "ad_rate": ad_rate,
            "return_rate": current_return_rate,
            "cover_days": cover_days,
            "inventory_turnover_days": cover_days,
            "return_growth_rate": return_growth,
            "risk": risk,
            "risk_types": risk_types,
            "risk_reason": "；".join(reasons) if reasons else "未触发断货或退货异常上涨预警",
        })

    current_rows = [row for row in rows if row["week_end"] == current_week]
    previous_rows = [row for row in rows if row["week_end"] == previous_week]
    current_sales = _sum(current_rows, "net_sales")
    previous_sales = _sum(previous_rows, "net_sales")
    current_shipped = _sum(current_rows, "shipped_units")
    current_returns = _sum(current_rows, "returned_units")
    ad_values = [_number(row.get("ad_spend")) for row in current_rows]
    known_ad_spend = sum(value for value in ad_values if value is not None)

    return {
        "current_sales": current_sales,
        "previous_sales": previous_sales,
        "sales_growth": (current_sales - previous_sales) / previous_sales if previous_sales else None,
        "return_rate": _rate(current_returns, current_shipped),
        "known_ad_spend": known_ad_spend,
        "ad_spend_missing": sum(value is None for value in ad_values),
        "ad_rate": _rate(known_ad_spend, current_sales),
        "rows": output_rows,
    }

