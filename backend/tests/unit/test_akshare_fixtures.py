"""A 股字段映射 fixture 回归测试（M2-17 / FR-DATA-07 / PRD §12.2）。

fixture（tests/fixtures/akshare_fields.json）固化了 2026-11-13 实测的
akshare 东财 emweb 年报列名与新浪 hq 行情字段。上游字段改名时：
1. 这里的映射断言会失败，提示同步改 provider；
2. 如果是有意变更，更新 fixture 并在变更日志说明。

测试全部离线：不 import akshare、不发网络请求，只对 fixture 与
provider 的映射表/解析函数做一致性校验。
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.providers.akshare_provider import (
    _BALANCE_FIELDS,
    _CASHFLOW_FIELDS,
    _PROFIT_FIELDS,
    _missing_fields,
    _num,
    _parse_time,
    _sina_as_of,
    _sina_symbol,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "akshare_fields.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


# ----------------------------------------------------------------------
# fixture 与 provider 映射表的一致性
# ----------------------------------------------------------------------
def test_profit_field_mapping_matches_fixture():
    fx = load_fixture()["akshare_financials"]
    for unified, candidates in _PROFIT_FIELDS.items():
        for col in candidates:
            assert col in fx["profit_columns"], (
                f"利润表映射 {unified} 引用的列 {col} 不在 fixture 中；"
                "若上游字段改名，请更新 app/providers/akshare_provider.py 与 fixture"
            )


def test_balance_field_mapping_matches_fixture():
    fx = load_fixture()["akshare_financials"]
    for unified, candidates in _BALANCE_FIELDS.items():
        for col in candidates:
            assert col in fx["balance_columns"], (
                f"资产负债表映射 {unified} 引用的列 {col} 不在 fixture 中"
            )


def test_cashflow_field_mapping_matches_fixture():
    fx = load_fixture()["akshare_financials"]
    for unified, candidates in _CASHFLOW_FIELDS.items():
        for col in candidates:
            assert col in fx["cashflow_columns"], (
                f"现金流量表映射 {unified} 引用的列 {col} 不在 fixture 中"
            )


def test_fixture_sample_row_parses_to_expected_values():
    """fixture 的样本值经过 _num 后应得到记录时的数值（单位：元）。"""
    sample = load_fixture()["akshare_financials"]["sample_row"]
    assert _num(sample["TOTAL_OPERATE_INCOME"]) == 172054171890.91
    assert _num(sample["OPERATE_COST"]) == 14892277570.91
    assert _num(sample["PARENT_NETPROFIT"]) == 82320067101.68
    assert _num(sample["BASIC_EPS"]) == 65.66
    assert _num(sample["TOTAL_LIABILITIES"]) == 49875590112.37
    assert _num(sample["NETCASH_OPERATE"]) == 61522204989.35


def test_report_date_parses():
    sample = load_fixture()["akshare_financials"]["sample_row"]
    assert _parse_time(sample["REPORT_DATE"]) == datetime(2025, 12, 31, tzinfo=UTC)


# ----------------------------------------------------------------------
# 新浪行情字段解析
# ----------------------------------------------------------------------
def test_sina_main_fields_parse():
    raw = load_fixture()["sina_quote"]["main"]
    fields = raw.split(",")
    # 0 名称 3 现价 30 日期 31 时间
    assert fields[0] == "贵州茅台"
    assert _num(fields[3]) == 1435.26
    assert _num(fields[8]) == 4177984  # 成交量（股）
    assert _sina_as_of(fields[30], fields[31]) == datetime(
        2026, 11, 13, 15, 34, 59, tzinfo=UTC
    )


def test_sina_ext_fields_parse():
    raw = load_fixture()["sina_quote"]["ext"]
    ext = raw.split(",")
    # 3 EPS-TTM 5 每股净资产 7 总股本(万股) 11 货币 24 52周 37 营收TTM
    assert _num(ext[3]) == 65.6615
    assert _num(ext[5]) == 216.9496
    assert _num(ext[7]) == 125008.1601  # 万股
    assert ext[11] == "CNY"
    week52 = ext[24].split("|")
    assert _num(week52[0]) == 1551.30
    assert _num(week52[1]) == 1269.24
    assert _num(ext[37]) == 174433934764.98  # 营收 TTM（元）


def test_sina_symbol_mapping():
    assert _sina_symbol("600519.SS") == "sh600519"
    assert _sina_symbol("000001.SZ") == "sz000001"
    assert _sina_symbol("830799.BJ") == "bj830799"
    assert _sina_symbol("600519") == "sh600519"
    assert _sina_symbol("000725") == "sz000725"


# ----------------------------------------------------------------------
# 缺失字段收集
# ----------------------------------------------------------------------
def test_missing_fields_lists_absent_important_fields():
    from app.providers.models import Quote

    empty = Quote(ticker="600519.SS", name="贵州茅台")
    missing = _missing_fields(empty)
    assert "price" in missing
    assert "market_cap" in missing
    assert "pe_ttm" in missing


def test_missing_fields_empty_when_complete():
    from app.providers.models import Quote

    full = Quote(
        ticker="600519.SS",
        name="贵州茅台",
        price=1435.26,
        previous_close=1410.27,
        market_cap=1.7e12,
        pe_ttm=21.9,
        eps_ttm=65.66,
        shares_outstanding=1.25e9,
    )
    assert _missing_fields(full) == []
