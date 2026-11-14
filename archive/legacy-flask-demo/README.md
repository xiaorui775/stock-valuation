# Legacy Flask Demo（已归档）

这是项目最初的 Flask + Chart.js 单页 Demo（`app.py` / `data_service.py` / `valuation.py` / `templates/` / `static/`）。

它已被 `backend/`（FastAPI）+ `frontend/`（React）取代，M1 结束后归档，不再维护、不再被任何构建或部署引用。

需要运行旧版只是为了对照行为时：

```bash
pip install -r requirements.txt
python app.py
```

新版覆盖了旧版全部四个接口（quote / history / financials / valuation），并有对应的回归测试：
`backend/tests/api/test_legacy_parity.py`。
