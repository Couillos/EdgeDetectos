#!/usr/bin/env python3
"""
Auto-generator de la documentation du langage de formule.
S'inspire du moteur (INDICATORS, parser, evaluateur) pour produire LANG.md.
Doit être ré-exécuté à chaque modification du moteur.

Usage: python generate_lang_doc.py
"""

import inspect
from pathlib import Path
from formula_engine import INDICATORS

# ─── Helpers d'analyse de signature ──────────────────────────────────

OHLCV_NAMES = {'open', 'high', 'low', 'close', 'volume'}
NUMERIC_TYPES = (int, float, type(None))


def _is_col_param(p):
    """Determine if a function parameter represents a column reference."""
    COL_NAMES = {'open', 'high', 'low', 'close', 'volume', 'col',
                 'open_col', 'high_col', 'low_col', 'close_col', 'volume_col'}
    if p.name in COL_NAMES:
        return True
    if p.name.endswith('_col'):
        return True
    if isinstance(p.default, str):
        return True  # string default → column name (e.g. col='close')
    return p.name[0] in ('h', 'l', 'o', 'c', 'v') and len(p.name) <= 6 and p.default is inspect.Parameter.empty


def _classify_args(fn):
    """Analyse la signature d'une fonction indicateur et retourne la liste
    des paramètres dans l'ordre, chacun classé comme 'col' ou 'num'.
    Retourne: [(nom_param, type, valeur_default, optionnel), ...]
    """
    sig = inspect.signature(fn)
    params = list(sig.parameters.values())
    result = []

    for p in params[1:]:  # skip 'data'
        is_optional = p.default is not inspect.Parameter.empty
        default = p.default if is_optional else None

        if _is_col_param(p):
            param_type = 'col'
        elif isinstance(default, NUMERIC_TYPES):
            param_type = 'num'
        else:
            param_type = 'num'

        result.append((p.name, param_type, default, is_optional))

    return result


def _build_formula_sig(name, args_info):
    """Build the formula signature string like: rsi(close, period)"""
    arg_strs = []
    for pname, ptype, default, optional in args_info:
        arg_strs.append(pname)
    return f'{name}({", ".join(arg_strs)})'


def _build_args_desc(args_info):
    """Build args shorthand preserving order: 'h, l, c, n'"""
    parts = []
    for pname, ptype, default, optional in args_info:
        if ptype == 'col':
            short = {
                'col': 'col', 'close': 'c', 'high': 'h', 'low': 'l',
                'open': 'o', 'volume': 'vol',
                'open_col': 'o', 'close_col': 'c',
            }.get(pname, pname[0])
        else:
            short = 'n'
        parts.append(short)
    return ', '.join(parts)


# ─── Génération ─────────────────────────────────────────────────────

def generate_lang_doc() -> str:
    lines = []
    lines.append('# Langage du Moteur de Formules')
    lines.append('')
    lines.append('Généré automatiquement depuis `formula_engine.py` — **ne pas éditer à la main**.')
    lines.append('Pour mettre à jour : `python generate_lang_doc.py`')
    lines.append('')

    # ── 1. Syntaxe générale ──
    lines.append('## Syntaxe générale')
    lines.append('')
    lines.append('| Élément | Syntaxe | Exemple |')
    lines.append('|---------|---------|---------|')
    lines.append('| Colonne OHLCV | `open`, `high`, `low`, `close`, `volume` | `close > open` |')
    lines.append('| Colonnes métriques | `funding_rate`, `open_interest`, `taker_buy_ratio`, `ls_ratio`, ... | `funding_rate < -0.01 & close < sma(close,20)` |')
    lines.append('| Nombre | `42`, `3.14`, `-1.5` | `period=14` |')
    lines.append('| Opérateur unaire | `-expr` | `-rsi(close,14)` |')
    lines.append('| Multiplication/Division | `*` `/` | `close * 0.98` |')
    lines.append('| Addition/Soustraction | `+` `-` | `close - sma(close,20)` |')
    lines.append('| Comparaison | `<` `>` `<=` `>=` `==` `!=` | `close < 30000` |')
    lines.append('| ET logique | `&` | `rsi(close,14) < 30 & close < bb_lower(close,20,2)` |')
    lines.append('| OU logique | `|` | `rsi(close,14) < 30 | close < bb_lower(close,20,2)` |')
    lines.append('| Parenthèses | `(expr)` | `(close - sma(close,20)) / sma(close,20) * 100` |')
    lines.append('| Shift | `.shift(N)` | `close.shift(6)`, `atr(high,low,close,14).shift(1)` |')
    lines.append('| Appel indicateur | `nom(arg1, arg2, ...)` | `sma(close, 20)` |')
    lines.append('')
    lines.append('**Règle importante** : les **colonnes** (open, high, low, close, volume, funding_rate, etc.) doivent être passées **par nom** (sans guillemets). Les **paramètres numériques** (period, seuil) sont passés en nombre.')
    lines.append('')

    # ── 2. Tous les indicateurs ──
    lines.append('## Indicateurs disponibles')
    lines.append('')
    lines.append(f'Total : {len(INDICATORS)} indicateurs.')
    lines.append('')

    categories = {}
    for name, info in sorted(INDICATORS.items()):
        cat = info['category']
        categories.setdefault(cat, []).append((name, info))

    for cat, items in categories.items():
        lines.append(f'### {cat} ({len(items)})')
        lines.append('')
        lines.append('| Formule | Args | Description |')
        lines.append('|---------|------|-------------|')

        for name, info in sorted(items):
            fn = info['fn']
            args_info = _classify_args(fn)
            formula_sig = _build_formula_sig(name, args_info)
            args_desc = _build_args_desc(args_info)
            desc = info['description']
            lines.append(f'| `{formula_sig}` | {args_desc} | {desc} |')

        lines.append('')

    # ── 2.1. Métriques disponibles ──
    lines.append('## Métriques disponibles')
    lines.append('')
    lines.append('Par défaut, les edges utilisent **OHLCV 1h**. Vous pouvez spécifier une autre métrique avec `--metric` et un autre timeframe avec `--timeframe`.')
    lines.append('')
    lines.append('| Métrique | Timeframes supportés | Colonnes disponibles |')
    lines.append('|----------|---------------------|---------------------|')
    lines.append('| `ohlcv` | 1m-1M | `open`, `high`, `low`, `close`, `volume` |')
    lines.append('| `funding_rate` | 2h, 4h, 8h | `funding_rate`, `mark_price` |')
    lines.append('| `open_interest` | 5m, 15m, 30m, 1h, 4h, 1d | `open_interest`, `open_interest_usd` |')
    lines.append('| `taker_volume` | 1m-1M | `taker_buy_base`, `taker_sell_base`, `taker_buy_quote`, `taker_sell_quote`, `taker_buy_ratio`, `taker_sell_ratio` |')
    lines.append('| `long_short_ratio` | 5m, 15m, 30m, 1h, 4h, 1d | `buy_ratio`, `sell_ratio`, `ls_ratio` |')
    lines.append('')
    lines.append('Les colonnes de la métrique sont mergées avec OHLCV et directement accessibles dans les formules.')
    lines.append('')
    lines.append('Exemple avec funding_rate:')
    lines.append('```bash')
    lines.append('python backtest.py --create-edge "Funding Squeeze" --long "funding_rate < -0.01 & close > ema(close, 50)" --metric funding_rate --timeframe 8h')
    lines.append('```')
    lines.append('')

    # ── 3. Valeur de retour ──
    lines.append('## Valeur de retour')
    lines.append('')
    lines.append('`eval_formula(formule, df)` retourne une `pd.Series` avec :')
    lines.append('')
    lines.append('| Valeur | Signification |')
    lines.append('|--------|---------------|')
    lines.append('| `1` | LONG (condition vraie) |')
    lines.append('| `0` | NEUTRAL (condition fausse) |')
    lines.append('| `-1` | SHORT (utilisé avec `--short`) |')
    lines.append('')

    # ── 4. CLI ──
    lines.append('## CLI')
    lines.append('')
    lines.append('```bash')
    lines.append('# Lister tous les indicateurs disponibles')
    lines.append('python backtest.py --list-indicators')
    lines.append('')
    lines.append('# Créer un edge long (OHLCV 1h par défaut)')
    lines.append('python backtest.py --create-edge "Nom" --long "votre_formule"')
    lines.append('')
    lines.append('# Créer un edge short (OHLCV 1h par défaut)')
    lines.append('python backtest.py --create-edge "Nom" --short "votre_formule"')
    lines.append('')
    lines.append('# Avec métrique et timeframe spécifiques')
    lines.append('python backtest.py --create-edge "Nom" --long "formule" --metric funding_rate --timeframe 8h')
    lines.append('')
    lines.append('# Avec horizons customs')
    lines.append('python backtest.py --create-edge "Nom" --long "formule" --horizons 1,4,6,12,24')
    lines.append('')
    lines.append('# Analyser un edge')
    lines.append('python backtest.py --analyze edges/nom.py')
    lines.append('')
    lines.append('# Classement de tous les edges')
    lines.append('python backtest.py --ranking')
    lines.append('')
    lines.append('# Analyse rapide (JSON only)')
    lines.append('python backtest.py --quick --analyze')
    lines.append('```')
    lines.append('')
    lines.append('**Important :** Un edge doit être explicitement **long** OU **short**, pas les deux.')
    lines.append('')

    # ── 5. Exemples ──
    lines.append('## Exemples de formules')
    lines.append('')
    lines.append('```bash')
    lines.append('# === OHLCV 1h (par défaut) ===')
    lines.append('python backtest.py --create-edge "RSI Oversold" --long "rsi(close,14) < 30"')
    lines.append('python backtest.py --create-edge "EMA50 Drop" --long "close < ema(close,50) * 0.98"')
    lines.append('python backtest.py --create-edge "ATR Breakout" --long "atr(high,low,close,14) > atr(high,low,close,14).shift(1) * 1.1"')
    lines.append('python backtest.py --create-edge "BB Squeeze" --long "bb_upper(close,20,2) - bb_lower(close,20,2) < atr(close,20)"')
    lines.append('python backtest.py --create-edge "MACD Momentum" --long "macd_hist(close,12,26,9) > 0"')
    lines.append('python backtest.py --create-edge "Multi Combo" --long "rsi(close,14) < 30 & close < bb_lower(close,20,2)"')
    lines.append('python backtest.py --create-edge "Bearish RSI" --short "rsi(close,14) > 70"')
    lines.append('')
    lines.append('# === Avec métriques avancées ===')
    lines.append('python backtest.py --create-edge "Funding Squeeze" --long "funding_rate < -0.01 & close > ema(close,50)" --metric funding_rate --timeframe 8h')
    lines.append('python backtest.py --create-edge "OI Expansion" --long "open_interest > open_interest.shift(24) & close > ema(close,50)" --metric open_interest --timeframe 1h')
    lines.append('python backtest.py --create-edge "Taker Buy Pressure" --long "taker_buy_ratio > 0.6 & close > open" --metric taker_volume --timeframe 1h')
    lines.append('python backtest.py --create-edge "LS Ratio Short" --short "ls_ratio < 0.8 & close < sma(close,200)" --metric long_short_ratio --timeframe 4h')
    lines.append('```')
    lines.append('')

    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    doc = generate_lang_doc()
    path = Path('LANG.md')
    path.write_text(doc)
    print(f'Documentation générée : {path.absolute()} ({len(doc.splitlines())} lignes)')
    print(f'Indicateurs : {len(INDICATORS)}')
    for cat in sorted(set(info['category'] for info in INDICATORS.values())):
        count = sum(1 for info in INDICATORS.values() if info['category'] == cat)
        print(f'  {cat}: {count}')
