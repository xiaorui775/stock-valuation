"""技术指标：纯计算，无 I/O（FR-CHART-03）。

所有函数在窗口期数据不足或输入缺失时返回 `None`，不填充、不插值。
指标口径与主流行情软件一致：

- MA(n)：前 n 个收盘价的简单平均，窗口不满时为 None。
- BOLL(n, k)：中轨 = MA(n)，上/下轨 = 中轨 ± k × 样本标准差（ddof=1，同 TA-Lib）。
- EMA(x, n)：seed = 前 n 个的 SMA，之后 ema = 前值 + α × (x − 前值)，α = 2/(n+1)。
- MACD(12, 26, 9)：DIF = EMA12 − EMA26，DEA = EMA9(DIF)，柱 = (DIF − DEA) × 2。
- RSI(n, Wilder)：U = max(Δ, 0)，D = max(−Δ, 0)，首值取前 n 个的简单平均，
  之后按 Wilder 平滑；RSI = U / (U + D) × 100，Δ=0 或 D=U=0 时为 50。
"""
from __future__ import annotations

from collections.abc import Sequence

MA_PERIODS = (5, 10, 20, 60, 120)
BOLL_PERIOD = 20
BOLL_K = 2.0
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
RSI_PERIOD = 14

def moving_average(closes: Sequence[float], n: int) -> list[float | None]:
    """简单移动平均；前 n−1 个位置窗口不满，为 None。"""
    out: list[float | None] = [None] * len(closes)
    if n <= 0:
        return out
    running = 0.0
    for i, close in enumerate(closes):
        running += close
        if i >= n:
            running -= closes[i - n]
        if i >= n - 1:
            out[i] = running / n
    return out

def ema(values: Sequence[float], n: int) -> list[float | None]:
    """指数移动平均：种子为前 n 个的 SMA，其后递推。"""
    out: list[float | None] = [None] * len(values)
    if n <= 0 or len(values) < n:
        return out
    seed = sum(values[:n]) / n
    out[n - 1] = seed
    alpha = 2.0 / (n + 1)
    prev = seed
    for i in range(n, len(values)):
        prev = prev + alpha * (values[i] - prev)
        out[i] = prev
    return out

def bollinger_bands(
    closes: Sequence[float], n: int = BOLL_PERIOD, k: float = BOLL_K
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """布林带（中轨、上轨、下轨）。标准差用样本口径（ddof=1）。"""
    ma = moving_average(closes, n)
    mid: list[float | None] = list(ma)
    upper: list[float | None] = [None] * len(closes)
    lower: list[float | None] = [None] * len(closes)
    for i in range(n - 1, len(closes)):
        window = closes[i - n + 1 : i + 1]
        mean = sum(window) / n
        variance = sum((x - mean) ** 2 for x in window) / (n - 1)
        std = variance ** 0.5
        upper[i] = mean + k * std
        lower[i] = mean - k * std
    return mid, upper, lower

def macd(
    closes: Sequence[float],
    fast: int = MACD_FAST,
    slow: int = MACD_SLOW,
    signal: int = MACD_SIGNAL,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """MACD：返回 (DIF, DEA, 柱)。柱 = (DIF − DEA) × 2，国内行情软件口径。"""
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    # DIF 只在两条 EMA 都就绪后才有值；DEA 是对 DIF 序列再做 EMA(signal)。
    dif: list[float | None] = [
        None if (f is None or s is None) else f - s for f, s in zip(ema_fast, ema_slow)
    ]
    defined = [d for d in dif if d is not None]
    dea_defined = ema(defined, signal) if len(defined) >= signal else [None] * len(defined)
    dea_map = {
        idx: value
        for idx, value in zip(
            (i for i, d in enumerate(dif) if d is not None), dea_defined
        )
    }
    dea: list[float | None] = [dea_map.get(i) for i in range(len(dif))]
    histogram = [
        None if (d is None or e is None) else (d - e) * 2 for d, e in zip(dif, dea)
    ]
    return dif, dea, histogram

def rsi(closes: Sequence[float], n: int = RSI_PERIOD) -> list[float | None]:
    """Wilder RSI。窗口不满返回 None；一段持平（Δ 全为 0）时为 50。"""
    out: list[float | None] = [None] * len(closes)
    if n <= 0 or len(closes) <= n:
        return out
    gains = losses = 0.0
    for i in range(1, n + 1):
        change = closes[i] - closes[i - 1]
        gains += max(change, 0.0)
        losses += max(-change, 0.0)
    avg_gain = gains / n
    avg_loss = losses / n
    out[n] = _rsi_value(avg_gain, avg_loss)
    for i in range(n + 1, len(closes)):
        change = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (n - 1) + max(change, 0.0)) / n
        avg_loss = (avg_loss * (n - 1) + max(-change, 0.0)) / n
        out[i] = _rsi_value(avg_gain, avg_loss)
    return out

def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_gain + avg_loss == 0:
        return 50.0
    return avg_gain / (avg_gain + avg_loss) * 100.0

def compute_all(closes: Sequence[float]) -> dict[str, list[float | None]]:
    """一次算齐图表需要的全部指标序列。

    返回 `{"ma5": [...], "boll_mid": [...], "dif": [...], "rsi14": [...]}`；
    输入为空时返回全 None 的空序列。调用方（history 接口）按 K 线对齐后输出。
    """
    result: dict[str, list[float | None]] = {}
    for n in MA_PERIODS:
        result[f"ma{n}"] = moving_average(closes, n)
    mid, upper, lower = bollinger_bands(closes)
    result["boll_mid"] = mid
    result["boll_upper"] = upper
    result["boll_lower"] = lower
    dif, dea, histogram = macd(closes)
    result["dif"] = dif
    result["dea"] = dea
    result["macd"] = histogram
    result["rsi14"] = rsi(closes)
    if not closes:
        return {key: [] for key in result}
    return result
