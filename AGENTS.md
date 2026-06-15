# Agent Rules — Edge Generator

## Architecture

```
CLI → formula_engine.py (eval_formula) → edges/<nom>.py → backtest.py --analyze → reports/<nom>/
```

Le fichier edge généré importe `eval_formula` depuis `formula_engine.py` et produit un `pd.Series` avec 1=LONG, -1=SHORT, 0=NEUTRAL.

---

## Langage de formule → LANG.md (auto-généré)

Tous les éléments de langage (indicateurs, opérateurs, shift, syntaxe) sont documentés dans **`LANG.md`**, généré automatiquement depuis le moteur.

**Avant de générer un edge via le CLI, TOUJOURS lire LANG.md** pour vérifier la disponibilité des indicateurs et la syntaxe.

---

## Règles impératives

### 1. Compléter le moteur AVANT de générer un edge

Si l'indicateur nécessaire n'existe pas dans `INDICATORS` (vérifier via `python backtest.py --list-indicators` ou dans `LANG.md`), **l'agent doit d'abord ajouter l'indicateur au moteur** puis utiliser la CLI.

**Ne JAMAIS écrire de pandas dans le fichier edge.** L'edge passe TOUJOURS par `eval_formula()`.

### 2. Ajouter un indicateur manquant

```python
@indicator('nom', 'Description', 'Catégorie', min_args, max_args)
def _mon_indicateur(data, col, period=14):
    return data[col].rolling(int(period)).mean()
```

Ajouter dans la bonne catégorie existante. Pour ta-lib : dans `_register_ta_indicators()`.

### 3. Tout ajout/modification → régénérer LANG.md

**Obligatoire** après chaque modification du moteur :

```bash
python generate_lang_doc.py
```

Valider que le nouvel indicateur apparaît dans `LANG.md`.

### 4. Test de validation

```bash
python -c "from formula_engine import eval_formula; import pandas as pd, numpy as np; ..."
python backtest.py --list-indicators
```

### 5. CLI

```bash
python backtest.py --create-edge "Nom" --long "formule" --short "formule" --horizons "1,4,6,12,24,48,72,168" --desc "..."
python backtest.py --quick --analyze
python backtest.py --analyze
python backtest.py --ranking
```

**Toujours utiliser les 8 horizons : 1, 4, 6, 12, 24, 48, 72, 168** (sauf cas explicitement contraire).

### 6. Multiprocessing

L'analyse utilise automatiquement **tous les cores CPU** disponibles via `multiprocessing.Pool`. Les données sont pré-computées et partagées via fichier parquet temporaire dans `/tmp/edge_analysis/`. Chaque worker process charge le registre des edges et la dataframe indépendamment.

```bash
# analyse rapide (JSON only, pas de charts)
python backtest.py --quick --analyze

# analyse complète avec charts
python backtest.py --analyze

# edge spécifique
python backtest.py --edge "Nom" --analyze
```

### 7. OOS Validation

```bash
python backtest.py --oos-validate --symbol BTC/USDT --since 2020-01-01 --until 2026-06-13
python backtest.py --oos-validate --symbol DOGE/USDT --since 2020-01-01 --until 2026-06-13
```

Valide tous les edges sur la période OOS (2025-01-31 → maintenant) et compare avec IS (2020-01-01 → 2025-01-31). Produit :
- `oos_{SYMBOL}.txt` — rapport texte avec verdicts, top/bottom edges, analyse de decay
- `oos_{SYMBOL}.csv` — données complètes pour analyse

Verdicts : `STRONG` (score ≥ 70), `PASS` (≥ 45), `WEAK` (≥ 25), `FAIL` (< 25).

### 8. Edge function names

Le CLI remplace automatiquement les tirets par des underscores dans les noms de fonction.
Ne JAMAIS éditer manuellement les fichiers edges/ — toujours utiliser `--create-edge`.

### 9. Market Structure Edges

Les edges de structure de marché (sans indicateurs) utilisent uniquement :
- `close`, `high`, `low`, `open`, `volume`
- `.shift(N)` pour les lookbacks
- `consecutive_green(N)`, `consecutive_red(N)`
- `higher_high(col, N)`, `lower_low(col, N)`
- `doji(open, close)`, `engulfing_bear(open, close)`, `engulfing_bull(open, close)`

Formules typiques : `close > high.shift(1)`, `low > low.shift(1) & close > close.shift(1)`
