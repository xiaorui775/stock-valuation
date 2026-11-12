"""股票估值工具（学习研究用途）。

运行：pip install -r requirements.txt && python app.py
可选：STOCKVAL_DEMO=1 python app.py  → 演示模式（内置样本数据，不联网）
"""

from flask import Flask, jsonify, render_template, request

import data_service
import valuation

app = Flask(__name__)


def _err(message, status=400):
    return jsonify({"error": message}), status


def _ticker_arg():
    return (request.args.get("ticker") or "").strip()


@app.route("/")
def index():
    return render_template("index.html", demo=data_service.DEMO_MODE)


@app.route("/api/quote")
def api_quote():
    ticker = _ticker_arg()
    if not ticker:
        return _err("请提供股票代码，例如 /api/quote?ticker=AAPL")
    try:
        return jsonify(data_service.get_quote(ticker))
    except data_service.DataError as exc:
        return _err(str(exc), 404)


@app.route("/api/history")
def api_history():
    ticker = _ticker_arg()
    if not ticker:
        return _err("请提供股票代码")
    try:
        points = data_service.get_history(ticker)
        return jsonify({"ticker": ticker.upper(), "points": points})
    except data_service.DataError as exc:
        return _err(str(exc), 404)


@app.route("/api/financials")
def api_financials():
    ticker = _ticker_arg()
    if not ticker:
        return _err("请提供股票代码")
    try:
        return jsonify(data_service.get_financials(ticker))
    except data_service.DataError as exc:
        return _err(str(exc), 404)


@app.route("/api/valuation")
def api_valuation():
    ticker = _ticker_arg()
    if not ticker:
        return _err("请提供股票代码")
    params = {}
    for key in ("growth", "terminal", "discount", "ddm_growth"):
        raw = request.args.get(key)
        if raw is not None and raw != "":
            try:
                params[key] = float(raw)
            except ValueError:
                return _err(f"参数 {key} 必须是数字")
    try:
        quote = data_service.get_quote(ticker)
        try:
            financials = data_service.get_financials(ticker)
        except data_service.DataError:
            financials = {"years": [], "balance_latest": {}}
        result = valuation.build_valuation(quote, financials, params)
        return jsonify(result)
    except data_service.DataError as exc:
        return _err(str(exc), 404)


@app.errorhandler(404)
def not_found(_e):
    if request.path.startswith("/api/"):
        return _err("接口不存在", 404)
    return render_template("index.html", demo=data_service.DEMO_MODE), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
