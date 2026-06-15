"""
Indicator implementations and registry.
"""

import numpy as np
import pandas as pd
from typing import Any, Callable, Dict, List, Optional

# ─── Registry ────────────────────────────────────────────────────────

INDICATORS: Dict[str, Dict] = {}


def indicator(name: str, description: str = '', category: str = '',
              min_args: int = 1, max_args: int = 5):
    def decorator(fn):
        INDICATORS[name] = {
            'fn': fn, 'description': description, 'category': category,
            'min_args': min_args, 'max_args': max_args,
        }
        return fn
    return decorator


def _get_index(data):
    for v in data.values():
        if isinstance(v, (pd.Series, pd.DataFrame)):
            return v.index
    return None


# ─── Trend ───────────────────────────────────────────────────────────

@indicator('sma', 'Simple Moving Average', 'Trend', 2, 2)
def _sma(data, col, period):
    return data[col].rolling(int(period)).mean()

@indicator('ema', 'Exponential Moving Average', 'Trend', 2, 2)
def _ema(data, col, period):
    return data[col].ewm(span=int(period), adjust=False).mean()

@indicator('wma', 'Weighted Moving Average', 'Trend', 2, 2)
def _wma(data, col, period):
    p = int(period)
    weights = np.arange(1, p + 1)
    def _calc(s):
        return np.dot(s, weights) / weights.sum() if len(s) == p else np.nan
    return data[col].rolling(p).apply(_calc, raw=True)

@indicator('hma', 'Hull Moving Average', 'Trend', 2, 2)
def _hma(data, col, period):
    p = int(period)
    half = int(p / 2)
    sqrt_p = int(np.sqrt(p))
    wma_half = _wma(data, col, half)
    wma_full = _wma(data, col, p)
    hull_data = {col: 2 * wma_half - wma_full}
    return _wma(hull_data, col, sqrt_p)

@indicator('dema', 'Double EMA', 'Trend', 2, 2)
def _dema(data, col, period):
    e1 = data[col].ewm(span=int(period), adjust=False).mean()
    e2 = e1.ewm(span=int(period), adjust=False).mean()
    return 2 * e1 - e2

@indicator('tema', 'Triple EMA', 'Trend', 2, 2)
def _tema(data, col, period):
    p = int(period)
    e1 = data[col].ewm(span=p, adjust=False).mean()
    e2 = e1.ewm(span=p, adjust=False).mean()
    e3 = e2.ewm(span=p, adjust=False).mean()
    return 3 * e1 - 3 * e2 + e3

@indicator('trima', 'Triangular Moving Average', 'Trend', 2, 2)
def _trima(data, col, period):
    p = int(period)
    sma1 = data[col].rolling(p).mean()
    return sma1.rolling(p).mean()


# ─── Momentum ────────────────────────────────────────────────────────

@indicator('rsi', 'Relative Strength Index', 'Momentum', 2, 2)
def _rsi(data, col, period=14):
    p = int(period)
    delta = data[col].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_g = gain.ewm(com=p - 1, min_periods=p).mean()
    avg_l = loss.ewm(com=p - 1, min_periods=p).mean()
    rs = avg_g / avg_l.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

@indicator('macd', 'MACD Line', 'Momentum', 1, 3)
def _macd(data, col, fast=12, slow=26):
    f = data[col].ewm(span=int(fast), adjust=False).mean()
    s = data[col].ewm(span=int(slow), adjust=False).mean()
    return f - s

@indicator('macd_signal', 'MACD Signal Line', 'Momentum', 1, 4)
def _macd_signal(data, col, fast=12, slow=26, signal=9):
    macd = _macd(data, col, fast, slow)
    return macd.ewm(span=int(signal), adjust=False).mean()

@indicator('macd_hist', 'MACD Histogram', 'Momentum', 1, 4)
def _macd_hist(data, col, fast=12, slow=26, signal=9):
    macd = _macd(data, col, fast, slow)
    sig = macd.ewm(span=int(signal), adjust=False).mean()
    return macd - sig

@indicator('stoch', 'Stochastic Oscillator %K', 'Momentum', 3, 4)
def _stoch(data, high, low, col='close', period=14):
    p = int(period)
    low_min = data[low].rolling(p).min()
    high_max = data[high].rolling(p).max()
    num = data[col] - low_min
    den = high_max - low_min
    return (num / den.replace(0, np.nan)) * 100

@indicator('stoch_rsi', 'Stochastic RSI', 'Momentum', 2, 3)
def _stoch_rsi(data, col, period=14, stoch_period=14):
    rsi = _rsi(data, col, period)
    p = int(stoch_period)
    rsi_min = rsi.rolling(p).min()
    rsi_max = rsi.rolling(p).max()
    return ((rsi - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan)) * 100

@indicator('williams_r', 'Williams %R', 'Momentum', 3, 3)
def _williams_r(data, high, low, col='close', period=14):
    p = int(period)
    hh = data[high].rolling(p).max()
    ll = data[low].rolling(p).min()
    return ((hh - data[col]) / (hh - ll).replace(0, np.nan)) * -100

@indicator('cci', 'Commodity Channel Index', 'Momentum', 3, 3)
def _cci(data, high, low, col='close', period=20):
    p = int(period)
    tp = (data[high] + data[low] + data[col]) / 3
    sma_tp = tp.rolling(p).mean()
    mad = tp.rolling(p).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - sma_tp) / (0.015 * mad.replace(0, np.nan))

@indicator('roc', 'Rate of Change', 'Momentum', 2, 2)
def _roc(data, col, period=12):
    p = int(period)
    return ((data[col] - data[col].shift(p)) / data[col].shift(p).replace(0, np.nan)) * 100

@indicator('tsi', 'True Strength Index', 'Momentum', 2, 3)
def _tsi(data, col, long=25, short=13):
    diff = data[col].diff()
    abs_diff = diff.abs()
    ema1 = diff.ewm(span=int(long)).mean()
    ema2 = ema1.ewm(span=int(short)).mean()
    ema_abs1 = abs_diff.ewm(span=int(long)).mean()
    ema_abs2 = ema_abs1.ewm(span=int(short)).mean()
    return (ema2 / ema_abs2.replace(0, np.nan)) * 100

@indicator('awesome_osc', 'Awesome Oscillator', 'Momentum', 2, 2)
def _awesome_osc(data, high, low):
    mid = (data[high] + data[low]) / 2
    return mid.rolling(5).mean() - mid.rolling(34).mean()

@indicator('uo', 'Ultimate Oscillator', 'Momentum', 3, 3)
def _uo(data, high, low, col='close'):
    bp = data[col] - np.minimum(data[low], data[col].shift(1))
    tr = np.maximum(data[high], data[col].shift(1)) - np.minimum(data[low], data[col].shift(1))
    avg7 = bp.rolling(7).sum() / tr.rolling(7).sum().replace(0, np.nan)
    avg14 = bp.rolling(14).sum() / tr.rolling(14).sum().replace(0, np.nan)
    avg28 = bp.rolling(28).sum() / tr.rolling(28).sum().replace(0, np.nan)
    return (4 * avg7 + 2 * avg14 + avg28) / (4 + 2 + 1) * 100


# ─── Volatility ──────────────────────────────────────────────────────

@indicator('bb_mid', 'Bollinger Band Middle', 'Volatility', 2, 2)
def _bb_mid(data, col, period=20):
    return data[col].rolling(int(period)).mean()

@indicator('bb_upper', 'Bollinger Band Upper', 'Volatility', 2, 3)
def _bb_upper(data, col, period=20, std=2):
    p = int(period)
    mid = data[col].rolling(p).mean()
    sd = data[col].rolling(p).std()
    return mid + float(std) * sd

@indicator('bb_lower', 'Bollinger Band Lower', 'Volatility', 2, 3)
def _bb_lower(data, col, period=20, std=2):
    p = int(period)
    mid = data[col].rolling(p).mean()
    sd = data[col].rolling(p).std()
    return mid - float(std) * sd

@indicator('atr', 'Average True Range', 'Volatility', 3, 2)
def _atr(data, high, low, col='close', period=14):
    p = int(period)
    tr = pd.concat([
        data[high] - data[low],
        (data[high] - data[col].shift(1)).abs(),
        (data[low] - data[col].shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(p).mean()

@indicator('keltner_mid', 'Keltner Channel Middle', 'Volatility', 3, 2)
def _keltner_mid(data, high, low, col='close', period=20):
    return _ema(data, col, period)

@indicator('keltner_upper', 'Keltner Channel Upper', 'Volatility', 3, 3)
def _keltner_upper(data, high, low, col='close', period=20, mult=2):
    mid = _ema(data, col, period)
    atr_val = _atr(data, high, low, col, period)
    return mid + float(mult) * atr_val

@indicator('keltner_lower', 'Keltner Channel Lower', 'Volatility', 3, 3)
def _keltner_lower(data, high, low, col='close', period=20, mult=2):
    mid = _ema(data, col, period)
    atr_val = _atr(data, high, low, col, period)
    return mid - float(mult) * atr_val

@indicator('donchian_upper', 'Donchian Channel Upper', 'Volatility', 3, 3)
def _donchian_upper(data, high, low, period=20):
    p = int(period)
    return data[high].rolling(p).max()

@indicator('donchian_lower', 'Donchian Channel Lower', 'Volatility', 3, 3)
def _donchian_lower(data, high, low, period=20):
    p = int(period)
    return data[low].rolling(p).min()

@indicator('donchian_mid', 'Donchian Channel Middle', 'Volatility', 3, 3)
def _donchian_mid(data, high, low, period=20):
    p = int(period)
    return (data[high].rolling(p).max() + data[low].rolling(p).min()) / 2


# ─── Volume ──────────────────────────────────────────────────────────

@indicator('obv', 'On-Balance Volume', 'Volume', 2, 1)
def _obv(data, col, volume='volume'):
    obv = (data[volume] * np.sign(data[col].diff())).fillna(0).cumsum()
    return obv

@indicator('volume_sma', 'Volume SMA', 'Volume', 1, 2)
def _volume_sma(data, col='volume', period=20):
    return data[col].rolling(int(period)).mean()

@indicator('mfi', 'Money Flow Index', 'Volume', 3, 2)
def _mfi(data, high, low, col='close', period=14):
    p = int(period)
    idx = data[col].index
    tp = (data[high] + data[low] + data[col]) / 3
    vol = data.get('volume', pd.Series(1, index=idx))
    mf = tp * vol
    pos = mf.where(tp > tp.shift(1), 0).rolling(p).sum()
    neg = mf.where(tp < tp.shift(1), 0).rolling(p).sum()
    return 100 - (100 / (1 + (pos / neg.replace(0, np.nan))))

@indicator('cmf', 'Chaikin Money Flow', 'Volume', 3, 2)
def _cmf(data, high, low, col='close', period=20):
    p = int(period)
    idx = data[col].index
    mfm = ((data[col] - data[low]) - (data[high] - data[col])) / (data[high] - data[low]).replace(0, np.nan)
    vol = data.get('volume', pd.Series(1, index=idx))
    mfv = mfm * vol
    return mfv.rolling(p).sum() / vol.rolling(p).sum().replace(0, np.nan)


# ─── Patterns ────────────────────────────────────────────────────────

@indicator('consecutive_red', 'Consecutive red candles', 'Pattern', 1, 1)
def _consecutive_red(data, n=3):
    red = (data['close'] < data['open']).astype(int)
    consec = red.groupby((red != red.shift()).cumsum()).cumsum() + 1
    return (consec >= int(n)).astype(int) * red

@indicator('consecutive_green', 'Consecutive green candles', 'Pattern', 1, 1)
def _consecutive_green(data, n=3):
    green = (data['close'] > data['open']).astype(int)
    consec = green.groupby((green != green.shift()).cumsum()).cumsum() + 1
    return (consec >= int(n)).astype(int) * green

@indicator('higher_high', 'Higher high pattern', 'Pattern', 1, 1)
def _higher_high(data, col='high', n=2):
    p = int(n)
    return (data[col] > data[col].shift(p)).astype(int)

@indicator('lower_low', 'Lower low pattern', 'Pattern', 1, 1)
def _lower_low(data, col='low', n=2):
    p = int(n)
    return (data[col] < data[col].shift(p)).astype(int)

@indicator('doji', 'Doji candle pattern', 'Pattern', 2, 2)
def _doji(data, open_col='open', close_col='close'):
    body = (data[close_col] - data[open_col]).abs()
    high_low = data.get('high', data[close_col]) - data.get('low', data[open_col])
    return (body / high_low.replace(0, np.nan) < 0.1).astype(int)

@indicator('engulfing_bull', 'Bullish Engulfing', 'Pattern', 2, 2)
def _engulfing_bull(data, open_col='open', close_col='close'):
    prev_red = data[close_col].shift(1) < data[open_col].shift(1)
    curr_green = data[close_col] > data[open_col]
    engulfs = data[open_col] < data[close_col].shift(1)
    engulfed = data[close_col] > data[open_col].shift(1)
    return (prev_red & curr_green & engulfs & engulfed).astype(int)

@indicator('engulfing_bear', 'Bearish Engulfing', 'Pattern', 2, 2)
def _engulfing_bear(data, open_col='open', close_col='close'):
    prev_green = data[close_col].shift(1) > data[open_col].shift(1)
    curr_red = data[close_col] < data[open_col]
    engulfs = data[open_col] > data[close_col].shift(1)
    engulfed = data[close_col] < data[open_col].shift(1)
    return (prev_green & curr_red & engulfs & engulfed).astype(int)


# ─── Cross / Crossover ───────────────────────────────────────────────

@indicator('cross_above', 'Cross above (a > b and a was <= b previously)', 'Pattern', 2, 2)
def _cross_above(data, col_a, col_b):
    a = data[col_a] if isinstance(col_a, str) else pd.Series(float(col_a), index=_get_index(data))
    b = data[col_b] if isinstance(col_b, str) else pd.Series(float(col_b), index=_get_index(data))
    return ((a > b) & (a.shift(1) <= b.shift(1))).astype(int)

@indicator('cross_below', 'Cross below (a < b and a was >= b previously)', 'Pattern', 2, 2)
def _cross_below(data, col_a, col_b):
    a = data[col_a] if isinstance(col_a, str) else pd.Series(float(col_a), index=_get_index(data))
    b = data[col_b] if isinstance(col_b, str) else pd.Series(float(col_b), index=_get_index(data))
    return ((a < b) & (a.shift(1) >= b.shift(1))).astype(int)


# ─── Rolling generics ────────────────────────────────────────────────

@indicator('rolling_max', 'Rolling maximum (any column)', 'Statistical', 2, 2)
def _rolling_max(data, col, period=20):
    return data[col].rolling(int(period)).max()

@indicator('rolling_min', 'Rolling minimum (any column)', 'Statistical', 2, 2)
def _rolling_min(data, col, period=20):
    return data[col].rolling(int(period)).min()

@indicator('rolling_sum', 'Rolling sum (any column)', 'Statistical', 2, 2)
def _rolling_sum(data, col, period=20):
    return data[col].rolling(int(period)).sum()

@indicator('rolling_std', 'Rolling standard deviation (any column)', 'Statistical', 2, 2)
def _rolling_std(data, col, period=20):
    return data[col].rolling(int(period)).std()

@indicator('highest', 'Highest value over period (any column, alias for rolling_max)', 'Statistical', 2, 2)
def _highest(data, col, period=20):
    return data[col].rolling(int(period)).max()

@indicator('lowest', 'Lowest value over period (any column, alias for rolling_min)', 'Statistical', 2, 2)
def _lowest(data, col, period=20):
    return data[col].rolling(int(period)).min()


# ─── Bars Since ──────────────────────────────────────────────────────

@indicator('bars_since', 'Bars since condition was last true', 'Statistical', 1, 1)
def _bars_since(data, condition_col):
    cond = data[condition_col].astype(bool)
    groups = cond.cumsum()
    result = groups.groupby(groups).cumcount()
    result[groups == 0] = np.nan
    return result


# ─── Between ─────────────────────────────────────────────────────────

@indicator('between', 'Check if value is between lower and upper bounds', 'Math', 3, 3)
def _between(data, col_val, col_lo, col_hi):
    val = data[col_val] if isinstance(col_val, str) else pd.Series(float(col_val), index=_get_index(data))
    lo = data[col_lo] if isinstance(col_lo, str) else pd.Series(float(col_lo), index=_get_index(data) or val.index)
    hi = data[col_hi] if isinstance(col_hi, str) else pd.Series(float(col_hi), index=_get_index(data) or val.index)
    return ((val >= lo) & (val <= hi)).astype(int)


# ─── Statistical ─────────────────────────────────────────────────────

@indicator('zscore', 'Z-Score', 'Statistical', 2, 2)
def _zscore(data, col, period=20):
    p = int(period)
    rolling_mean = data[col].rolling(p).mean()
    rolling_std = data[col].rolling(p).std()
    return (data[col] - rolling_mean) / rolling_std.replace(0, np.nan)

@indicator('percentile', 'Percentile Rank', 'Statistical', 2, 2)
def _percentile(data, col, period=20):
    p = int(period)
    return data[col].rolling(p).apply(lambda x: (x[-1] > x).sum() / len(x) * 100, raw=True)

@indicator('vwap', 'Volume Weighted Average Price', 'Statistical', 2, 2)
def _vwap(data, col='close', volume='volume'):
    idx = data[col].index
    vol = data.get(volume, pd.Series(1, index=idx))
    return (data[col] * vol).cumsum() / vol.cumsum().replace(0, np.nan)


# ─── ADX ─────────────────────────────────────────────────────────────

@indicator('adx', 'Average Directional Index', 'Momentum', 3, 2)
def _adx(data, high, low, col='close', period=14):
    p = int(period)
    tr = _atr(data, high, low, col, p)
    up = data[high] - data[high].shift(1)
    down = data[low].shift(1) - data[low]
    plus_dm = ((up > down) & (up > 0)).astype(int) * up
    minus_dm = ((down > up) & (down > 0)).astype(int) * down
    plus_di = (plus_dm.rolling(p).mean() / tr.replace(0, np.nan)) * 100
    minus_di = (minus_dm.rolling(p).mean() / tr.replace(0, np.nan)) * 100
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
    return dx.rolling(p).mean()


# ─── Time ────────────────────────────────────────────────────────────

@indicator('hour', 'Current hour (0-23) from DatetimeIndex', 'Time', 0, 0)
def _hour(data):
    idx = _get_index(data)
    return pd.Series(idx.hour, index=idx)

@indicator('minute', 'Current minute (0-59) from DatetimeIndex', 'Time', 0, 0)
def _minute(data):
    idx = _get_index(data)
    return pd.Series(idx.minute, index=idx)

@indicator('dayofweek', 'Day of week (0=Monday, 6=Sunday) from DatetimeIndex', 'Time', 0, 0)
def _dayofweek(data):
    idx = _get_index(data)
    return pd.Series(idx.dayofweek, index=idx)

@indicator('is_weekend', '1 if Saturday/Sunday, 0 otherwise', 'Time', 0, 0)
def _is_weekend(data):
    idx = _get_index(data)
    return pd.Series((idx.dayofweek >= 5).astype(int), index=idx)


# ─── Math wrappers ───────────────────────────────────────────────────

@indicator('log', 'Natural logarithm', 'Math', 1, 1)
def _log(data, col): return np.log(data[col].clip(lower=1e-10))

@indicator('exp', 'Exponential', 'Math', 1, 1)
def _exp(data, col): return np.exp(data[col])

@indicator('sqrt', 'Square root', 'Math', 1, 1)
def _sqrt(data, col): return np.sqrt(data[col].clip(lower=0))

@indicator('abs', 'Absolute value', 'Math', 1, 1)
def _abs(data, col): return data[col].abs()

@indicator('sign', 'Sign function', 'Math', 1, 1)
def _sign(data, col): return np.sign(data[col])

@indicator('min', 'Minimum of two series', 'Math', 2, 2)
def _min(data, col1, col2): return np.minimum(data[col1], data[col2])

@indicator('max', 'Maximum of two series', 'Math', 2, 2)
def _max(data, col1, col2): return np.maximum(data[col1], data[col2])


# ─── ta-lib Integration ──────────────────────────────────────────────

def _register_ta_indicators():
    try:
        import ta.trend, ta.momentum, ta.volatility, ta.volume
    except ImportError:
        return

    @indicator('adx', 'Average Directional Index (ta)', 'Trend', 3, 3)
    def _adx_ta(data, high, low, close, period=14):
        return ta.trend.adx(data[high], data[low], data[close], int(period))

    @indicator('adx_pos', 'ADX Positive Directional (ta)', 'Trend', 3, 3)
    def _adx_pos_ta(data, high, low, close, period=14):
        return ta.trend.adx_pos(data[high], data[low], data[close], int(period))

    @indicator('adx_neg', 'ADX Negative Directional (ta)', 'Trend', 3, 3)
    def _adx_neg_ta(data, high, low, close, period=14):
        return ta.trend.adx_neg(data[high], data[low], data[close], int(period))

    @indicator('aroon_up', 'Aroon Up (ta)', 'Trend', 2, 2)
    def _aroon_up_ta(data, high, low, period=25):
        return ta.trend.aroon_up(data[high], data[low], int(period))

    @indicator('aroon_down', 'Aroon Down (ta)', 'Trend', 2, 2)
    def _aroon_down_ta(data, high, low, period=25):
        return ta.trend.aroon_down(data[high], data[low], int(period))

    @indicator('kama', 'Kaufman Adaptive MA (ta)', 'Trend', 2, 2)
    def _kama_ta(data, col, period=10):
        return ta.momentum.kama(data[col], int(period))

    @indicator('trix', 'Trix (ta)', 'Trend', 2, 2)
    def _trix_ta(data, col, period=15):
        return ta.trend.trix(data[col], int(period))

    @indicator('vortex_pos', 'Vortex Positive (ta)', 'Trend', 3, 3)
    def _vortex_pos_ta(data, high, low, close, period=14):
        return ta.trend.vortex_indicator_pos(data[high], data[low], data[close], int(period))

    @indicator('vortex_neg', 'Vortex Negative (ta)', 'Trend', 3, 3)
    def _vortex_neg_ta(data, high, low, close, period=14):
        return ta.trend.vortex_indicator_neg(data[high], data[low], data[close], int(period))

    @indicator('psar_up', 'Parabolic SAR Up (ta)', 'Trend', 3, 3)
    def _psar_up_ta(data, high, low, close):
        return ta.trend.psar_up(data[high], data[low], data[close])

    @indicator('psar_down', 'Parabolic SAR Down (ta)', 'Trend', 3, 3)
    def _psar_down_ta(data, high, low, close):
        return ta.trend.psar_down(data[high], data[low], data[close])

    @indicator('ichimoku_a', 'Ichimoku Conversion A (ta)', 'Trend', 2, 2)
    def _ichimoku_a_ta(data, high, low):
        return ta.trend.ichimoku_a(data[high], data[low])

    @indicator('ichimoku_b', 'Ichimoku Conversion B (ta)', 'Trend', 2, 2)
    def _ichimoku_b_ta(data, high, low):
        return ta.trend.ichimoku_b(data[high], data[low])

    @indicator('ichimoku_base', 'Ichimoku Base Line (ta)', 'Trend', 2, 2)
    def _ichimoku_base_ta(data, high, low, period=26):
        return ta.trend.ichimoku_base_line(data[high], data[low], int(period))

    @indicator('ichimoku_conversion', 'Ichimoku Conversion (ta)', 'Trend', 2, 2)
    def _ichimoku_conversion_ta(data, high, low, period=9):
        return ta.trend.ichimoku_conversion_line(data[high], data[low], int(period))

    @indicator('mass_index', 'Mass Index (ta)', 'Trend', 3, 3)
    def _mass_index_ta(data, high, low, period=9):
        return ta.trend.mass_index(data[high], data[low], int(period))

    @indicator('stc', 'Schaff Trend Cycle (ta)', 'Trend', 2, 2)
    def _stc_ta(data, col, period=10):
        return ta.trend.stc(data[col], int(period))

    @indicator('ppo', 'Percentage Price Oscillator (ta)', 'Momentum', 2, 3)
    def _ppo_ta(data, col, fast=12, slow=26):
        return ta.momentum.ppo(data[col], int(fast), int(slow))

    @indicator('ppo_signal', 'PPO Signal Line (ta)', 'Momentum', 2, 4)
    def _ppo_signal_ta(data, col, fast=12, slow=26, signal=9):
        return ta.momentum.ppo_signal(data[col], int(fast), int(slow), int(signal))

    @indicator('ppo_hist', 'PPO Histogram (ta)', 'Momentum', 2, 4)
    def _ppo_hist_ta(data, col, fast=12, slow=26, signal=9):
        return ta.momentum.ppo_hist(data[col], int(fast), int(slow), int(signal))

    @indicator('pvo', 'Percentage Volume Oscillator (ta)', 'Momentum', 2, 3)
    def _pvo_ta(data, volume, fast=12, slow=26):
        return ta.momentum.pvo(data[volume], int(fast), int(slow))

    @indicator('pvo_signal', 'PVO Signal Line (ta)', 'Momentum', 2, 4)
    def _pvo_signal_ta(data, volume, fast=12, slow=26, signal=9):
        return ta.momentum.pvo_signal(data[volume], int(fast), int(slow), int(signal))

    @indicator('pvo_hist', 'PVO Histogram (ta)', 'Momentum', 2, 4)
    def _pvo_hist_ta(data, volume, fast=12, slow=26, signal=9):
        return ta.momentum.pvo_hist(data[volume], int(fast), int(slow), int(signal))

    @indicator('stochrsi_k', 'StochRSI %K (ta)', 'Momentum', 2, 2)
    def _stochrsi_k_ta(data, col, period=14):
        return ta.momentum.stochrsi_k(data[col], int(period))

    @indicator('stochrsi_d', 'StochRSI %D (ta)', 'Momentum', 2, 2)
    def _stochrsi_d_ta(data, col, period=14):
        return ta.momentum.stochrsi_d(data[col], int(period))

    @indicator('ulcer_index', 'Ulcer Index (ta)', 'Volatility', 2, 2)
    def _ulcer_ta(data, col, period=14):
        return ta.volatility.ulcer_index(data[col], int(period))

    @indicator('force_index', 'Force Index (ta)', 'Volume', 2, 2)
    def _force_index_ta(data, col, volume, period=13):
        return ta.volume.force_index(data[col], data[volume], int(period))

    @indicator('ease_of_movement', 'Ease of Movement (ta)', 'Volume', 3, 3)
    def _eom_ta(data, high, low, volume, period=14):
        return ta.volume.ease_of_movement(data[high], data[low], data[volume], int(period))

    @indicator('acc_dist_index', 'Accumulation/Distribution (ta)', 'Volume', 3, 3)
    def _adi_ta(data, high, low, col, volume):
        return ta.volume.acc_dist_index(data[high], data[low], data[col], data[volume])

    @indicator('nvi', 'Negative Volume Index (ta)', 'Volume', 2, 2)
    def _nvi_ta(data, col, volume):
        return ta.volume.negative_volume_index(data[col], data[volume])

    @indicator('vpt', 'Volume Price Trend (ta)', 'Volume', 2, 2)
    def _vpt_ta(data, col, volume):
        return ta.volume.volume_price_trend(data[col], data[volume])


_register_ta_indicators()
