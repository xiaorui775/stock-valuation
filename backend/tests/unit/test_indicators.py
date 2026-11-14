"""技术指标单元测试：口径、窗口期与 None 语义（FR-CHART-03）。"""
from __future__ import annotations

import math

import pytest

from app.analysis.indicators import (
    bollinger_bands,
    compute_all,
    ema,
    macd,
    moving_average,
    rsi,
)

# 一段可手工核对的收盘价（斐波那契前 12 项）
CLOSES = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]


def test_ma_window_not_full_is_none():
    ma = moving_average(CLOSES, 5)
    assert ma[3] is None
    # 第 5 个位置（下标 4）= (1+1+2+3+5)/5
    assert ma[4] == pytest.approx(2.4)
    assert ma[-1] == pytest.approx(sum(CLOSES[-5:]) / 5)


def test_ma_matches_bruteforce():
    for n in (5, 10, 20, 60, 120):
        ma = moving_average(CLOSES, n)
        for i in range(len(CLOSES)):
            if i >= n - 1:
                assert ma[i] == pytest.approx(sum(CLOSES[i - n + 1 : i + 1]) / n)
            else:
                assert ma[i] is None


def test_ema_seed_is_sma_and_recurrence_holds():
    out = ema(CLOSES, 5)
    assert out[3] is None
    assert out[4] == pytest.approx(2.4)
    alpha = 2 / 6
    expected = out[4]
    for i in range(5, len(CLOSES)):
        expected = expected + alpha * (CLOSES[i] - expected)
        assert out[i] == pytest.approx(expected)


def test_bollinger_bands_are_mean_plus_minus_k_std():
    closes = [10.0] * 19 + [12.0]
    mid, upper, lower = bollinger_bands(closes, n=20, k=2.0)
    assert mid[:19] == [None] * 19
    assert mid[19] == pytest.approx(10.1)
    # 前 19 个是 10、第 20 个是 12：样本方差 = (19×0.1² + 1.9²) / 19 = 0.2
    std = math.sqrt(0.2)
    assert upper[19] == pytest.approx(10.1 + 2 * std)
    assert lower[19] == pytest.approx(10.1 - 2 * std)


def test_bollinger_matches_bruteforce_std():
    mid, upper, lower = bollinger_bands(CLOSES, n=5, k=2.0)
    for i in range(4, len(CLOSES)):
        window = CLOSES[i - 4 : i + 1]
        mean = sum(window) / 5
        std = math.sqrt(sum((x - mean) ** 2 for x in window) / 4)
        assert mid[i] == pytest.approx(mean)
        assert upper[i] == pytest.approx(mean + 2 * std)
        assert lower[i] == pytest.approx(mean - 2 * std)


def test_macd_dif_is_ema12_minus_ema26():
    closes = [float(i + 1) for i in range(60)]
    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    dif, dea, hist = macd(closes)
    for i in range(len(closes)):
        if ema12[i] is None or ema26[i] is None:
            assert dif[i] is None
        else:
            assert dif[i] == pytest.approx(ema12[i] - ema26[i])
    # DEA 在 DIF 连续就绪 signal 根之后才出现
    first_defined = next(i for i, d in enumerate(dif) if d is not None)
    defined = [d for d in dif if d is not None]
    expected_dea = sum(defined[:9]) / 9
    first_dea_index = first_defined + 8
    assert dea[first_dea_index] == pytest.approx(expected_dea)
    assert dea[first_dea_index - 1] is None
    # 柱 = (DIF − DEA) × 2
    if dea[first_dea_index] is not None:
        assert hist[first_dea_index] == pytest.approx(
            (dif[first_dea_index] - dea[first_dea_index]) * 2
        )


def test_rsi_matches_manual_wilder_computation():
    closes = [44.0, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42,
              45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00,
              46.03, 46.41, 46.22, 45.64]
    out = rsi(closes, n=14)
    # 手工核对：首 14 个差分里涨 3.62 / 跌 1.34 → RSI = 3.62/(3.62+1.34)×100 ≈ 72.98
    assert out[14] == pytest.approx(72.98, abs=0.02)
    # 之后按 Wilder 平滑递推，不再等于首值但可由公式重算
    assert out[15] is not None and out[15] != out[14]
    assert out[:14] == [None] * 14


def test_rsi_flat_series_is_50():
    out = rsi([10.0] * 30, n=14)
    assert out[14] == 50.0
    assert out[-1] == 50.0


def test_rsi_short_series_is_all_none():
    assert rsi([1.0, 2.0], n=14) == [None, None]


def test_compute_all_keys_and_alignment():
    result = compute_all([float(i) for i in range(130)])
    for key in ("ma5", "ma10", "ma20", "ma60", "ma120", "boll_mid", "boll_upper",
                "boll_lower", "dif", "dea", "macd", "rsi14"):
        assert key in result
        assert len(result[key]) == 130
    assert result["ma5"][4] is not None
    # 130 根已满 120 窗口：窗口不满的位置为 None，第 120 根（下标 119）刚好就绪
    assert result["ma120"][118] is None
    assert result["ma120"][119] == pytest.approx(sum(range(120)) / 120)


def test_compute_all_empty_input():
    result = compute_all([])
    assert result == {} or all(v == [] for v in result.values())
