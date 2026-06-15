"""
Core analysis: forward returns, horizon stats, rolling/yearly/vol regime stats.
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Optional, Tuple

DEFAULT_HORIZONS = [1, 4, 6, 12, 24, 48, 72, 168]
HORIZON_LABELS = ['1h', '4h', '6h', '12h', '24h', '48h', '72h', '168h']
REPORTS_DIR = 'reports'


def _to_native(v):
    if isinstance(v, (np.generic,)):
        return v.item()
    if isinstance(v, (np.ndarray,)):
        return v.tolist()
    return v


def compute_forward_returns(df: pd.DataFrame,
                            horizons: Optional[List[int]] = None) -> pd.DataFrame:
    if horizons is None:
        horizons = DEFAULT_HORIZONS
    for h in horizons:
        df[f'fwd_{h}h'] = (df['close'].shift(-h) - df['close']) / df['close'] * 100
    return df


def bootstrap_ci(data: np.ndarray, n_boot: int = 1000) -> Tuple[float, float]:
    boot_means = []
    for _ in range(n_boot):
        sample = np.random.choice(data, size=len(data), replace=True)
        boot_means.append(np.mean(sample))
    return (float(np.percentile(boot_means, 2.5)),
            float(np.percentile(boot_means, 97.5)))


def monte_carlo_permutation(signal_rets: np.ndarray,
                            all_rets: np.ndarray,
                            n_iter: int = 1000) -> Tuple[float, float, np.ndarray]:
    np.random.seed(42)
    n = len(signal_rets)
    if n > len(all_rets):
        return 1.0, float(np.mean(all_rets)), np.array([np.nan])
    mc_means = []
    for _ in range(n_iter):
        sample = np.random.choice(all_rets, size=n, replace=False)
        mc_means.append(np.mean(sample))
    mc_means = np.array(mc_means)
    mc_p = (mc_means >= np.mean(signal_rets)).mean()
    return mc_p, float(np.mean(mc_means)), mc_means


def _signal_returns(df: pd.DataFrame, signal_col: str, h: int) -> pd.Series:
    mask = df[signal_col] != 0
    return (df.loc[mask, f'fwd_{h}h'] * df.loc[mask, signal_col]).dropna()


def compute_horizon_stats(df: pd.DataFrame,
                          signal_col: str,
                          h: int) -> Dict:
    sr = _signal_returns(df, signal_col, h)
    ar = df[f'fwd_{h}h'].dropna()

    results = {
        'horizon': h,
        'n_signals': len(sr),
        'mean': float(sr.mean()) if len(sr) > 0 else np.nan,
        'median': float(sr.median()) if len(sr) > 0 else np.nan,
        'std': float(sr.std()) if len(sr) > 1 else np.nan,
        'winrate': float((sr > 0).mean() * 100) if len(sr) > 0 else np.nan,
        'skew': float(sr.skew()) if len(sr) > 2 else np.nan,
        'p5': float(np.percentile(sr, 5)) if len(sr) > 0 else np.nan,
        'p95': float(np.percentile(sr, 95)) if len(sr) > 0 else np.nan,
    }

    if len(sr) < 3:
        results.update({
            't_stat': np.nan, 't_p': np.nan,
            'ks_stat': np.nan, 'ks_p': np.nan,
            'mc_p': np.nan, 'mc_mean': np.nan,
            'ci_low': np.nan, 'ci_high': np.nan,
            'sharpe': np.nan, 'total_return': np.nan,
        })
        return results

    t_stat, t_p = stats.ttest_1samp(sr, 0)
    ks_stat, ks_p = stats.ks_2samp(sr, ar)
    mc_p, mc_mean, _ = monte_carlo_permutation(sr.values, ar.values)
    ci_low, ci_high = bootstrap_ci(sr.values)
    sharpe = float(sr.mean() / sr.std()) if sr.std() > 0 else 0.0
    total_ret = float(sr.sum())

    results.update({
        't_stat': float(t_stat),
        't_p': float(t_p),
        'ks_stat': float(ks_stat),
        'ks_p': float(ks_p),
        'mc_p': float(mc_p),
        'mc_mean': float(mc_mean),
        'ci_low': float(ci_low),
        'ci_high': float(ci_high),
        'sharpe': float(sharpe),
        'total_return': total_ret,
    })
    return results


def compute_rolling_stats(df: pd.DataFrame, signal_col: str,
                          window: int = 5040, step: int = 720) -> pd.DataFrame:
    if len(df) < window:
        return pd.DataFrame()

    mask = df[signal_col] != 0
    dir_ret = pd.Series(0.0, index=df.index)
    dir_ret[mask] = (df.loc[mask, 'fwd_24h'] * df.loc[mask, signal_col])
    sig_count = mask.astype(int)

    n_windows = (len(df) - window) // step + 1
    dates = np.empty(n_windows, dtype=object)
    means = np.empty(n_windows)
    winrates = np.empty(n_windows)
    counts = np.empty(n_windows, dtype=int)
    sharpes = np.empty(n_windows)

    for idx, start in enumerate(range(0, len(df) - window, step)):
        end = start + window
        sub_ret = dir_ret.iloc[start:end]
        sub_sig = sig_count.iloc[start:end]
        sig_mask = sub_ret != 0
        n_sig = sig_mask.sum()

        dates[idx] = df.index[end - 1]
        counts[idx] = int(sub_sig.sum())

        if n_sig > 20:
            sr = sub_ret[sig_mask]
            m = float(sr.mean())
            means[idx] = m
            winrates[idx] = float((sr > 0).mean() * 100)
            sharpes[idx] = float(m / sr.std()) if sr.std() > 0 else 0.0
        else:
            means[idx] = np.nan
            winrates[idx] = np.nan
            sharpes[idx] = np.nan

    valid = ~np.isnan(means)
    return pd.DataFrame({
        'date': pd.to_datetime([d for d, v in zip(dates, valid) if v]),
        'mean': means[valid],
        'winrate': winrates[valid],
        'count': counts[valid],
        'sharpe': sharpes[valid],
    })


def compute_yearly_stats(df: pd.DataFrame, signal_col: str) -> pd.DataFrame:
    results = []
    for year, grp in df.groupby(df.index.year):
        sr = _signal_returns(grp, signal_col, 24)
        if len(sr) > 5:
            t_stat, t_p = stats.ttest_1samp(sr, 0)
            results.append({
                'year': year,
                'n': len(sr),
                'mean': float(sr.mean()),
                'winrate': float((sr > 0).mean() * 100),
                'p_value': float(t_p),
                'sharpe': float(sr.mean() / sr.std()) if sr.std() > 0 else 0,
            })
    return pd.DataFrame(results)


def compute_vol_regime_stats(df: pd.DataFrame, signal_col: str) -> pd.DataFrame:
    df = df.copy()
    df['realized_vol_24h'] = df['close'].pct_change().rolling(24).std() * np.sqrt(24) * 100
    df['vol_regime'] = pd.qcut(df['realized_vol_24h'], 3,
                                labels=['Low', 'Mid', 'High'], duplicates='drop')

    results = []
    for regime, grp in df.groupby('vol_regime', observed=True):
        sr = _signal_returns(grp, signal_col, 24)
        ar = grp['fwd_24h'].dropna()
        if len(sr) > 10:
            t_stat, t_p = stats.ttest_1samp(sr, 0)
            excess = float(sr.mean() - ar.mean())
            results.append({
                'regime': regime,
                'n': len(sr),
                'mean': float(sr.mean()),
                'excess_vs_random': excess,
                'winrate': float((sr > 0).mean() * 100),
                'p_value': float(t_p),
            })
    return pd.DataFrame(results)


def _equity_curve(df: pd.DataFrame, signal_col: str, h: int,
                  max_horizon: Optional[int] = None) -> pd.Series:
    sig_mask = df[signal_col] != 0
    if sig_mask.sum() == 0:
        return pd.Series(dtype=float)
    dir_rets = df.loc[sig_mask, f'fwd_{h}h'] * df.loc[sig_mask, signal_col]
    timestamps = df.index[sig_mask.values]
    trim = max_horizon if max_horizon else h
    if trim < len(dir_rets):
        dir_rets = dir_rets.iloc[:-trim]
        timestamps = timestamps[:-trim]
    return pd.Series(np.cumsum(dir_rets.values), index=timestamps, name=f'h={h}')


def analyze_signal(df: pd.DataFrame, signal_col: str,
                   horizons: Optional[List[int]] = None) -> Dict:
    if horizons is None:
        horizons = DEFAULT_HORIZONS
    if not any(c.startswith('fwd_') for c in df.columns):
        df = compute_forward_returns(df, horizons)

    horizon_stats = {}
    for h in horizons:
        horizon_stats[h] = compute_horizon_stats(df, signal_col, h)

    rolling = compute_rolling_stats(df, signal_col)
    yearly = compute_yearly_stats(df, signal_col)
    vol_regime = compute_vol_regime_stats(df, signal_col)

    equity_curves: Dict[int, pd.Series] = {}
    max_h = max(horizons)
    for h in horizons:
        ec = _equity_curve(df, signal_col, h, max_horizon=max_h)
        if len(ec) > 0:
            equity_curves[h] = ec

    signal_rets_by_h: Dict[int, pd.Series] = {}
    all_rets_by_h: Dict[int, pd.Series] = {}
    for h in horizons:
        signal_rets_by_h[h] = _signal_returns(df, signal_col, h)
        all_rets_by_h[h] = df[f'fwd_{h}h'].dropna()

    signal_count = int((df[signal_col] != 0).sum())

    best_h = None
    best_score = -np.inf
    for h in horizons:
        s = horizon_stats.get(h, {})
        if s.get('n_signals', 0) > 10:
            sh = s.get('sharpe', np.nan)
            mc = s.get('mc_p', 1)
            if not np.isnan(sh):
                score = sh * 10 + (1 - mc) * 5
                if score > best_score:
                    best_score = score
                    best_h = h

    return {
        'df': df,
        'signal_col': signal_col,
        'horizon_stats': horizon_stats,
        'rolling': rolling,
        'yearly': yearly,
        'vol_regime': vol_regime,
        'equity_curves': equity_curves,
        'signal_rets_by_h': signal_rets_by_h,
        'all_rets_by_h': all_rets_by_h,
        'signal_count': signal_count,
        'signal_pct': float(signal_count / max(len(df), 1) * 100),
        'best_horizon': best_h,
    }
