"""规则化财务解读与组合汇总（纯计算）。"""
from app.analysis.financial_insights import RULES, analyze
from app.analysis.portfolio import HoldingRow, holding_metrics, summarize

__all__ = ["RULES", "HoldingRow", "analyze", "holding_metrics", "summarize"]
