---
name: add-edge
description: Ajouter un nouvel edge de trading à backtest.py pour tester des conditions d'entrée long/short sur BTC.
---

# Ajouter un Edge de Trading

Ce skill vous guide pour ajouter un nouvel edge au système de backtesting `backtest.py`.

## Structure d'un Edge

Un edge est défini par :
- **name** : nom unique
- **entry_condition** : fonction qui reçoit un DataFrame OHLCV et retourne une `pd.Series` avec `1` (LONG), `-1` (SHORT), ou `0` (NEUTRAL)
- **close_horizons** : liste d'horizons de clôture en heures (défaut: `[1, 2, 4, 8, 12, 24]`)

## Méthode 1 : Fichier dédié (recommandé)

Créez un fichier dans `edges/<nom_edge>.py` :

```python
import pandas as pd
from backtest import register_edge, Edge

def my_condition(df: pd.DataFrame) -> pd.Series:
    # df columns: open, high, low, close, volume
    # index: datetime
    signals = pd.Series(0, index=df.index)
    
    # Exemple : Long quand le RSI < 25, Short quand RSI > 75
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_g = gain.rolling(14).mean()
    avg_l = loss.rolling(14).mean()
    rsi = 100 - (100 / (1 + avg_g / avg_l))
    
    signals[rsi < 25] = 1
    signals[rsi > 75] = -1
    return signals

def register():
    register_edge(Edge(
        name="RSI 14 Extreme",
        entry_condition=my_condition,
        close_horizons=[1, 3, 6, 12, 24, 48],
        description="Long RSI<25, Short RSI>75",
    ))
```

Le fichier est automatiquement chargé au lancement de `backtest.py`.

## Méthode 2 : Inline dans backtest.py

Ajoutez directement dans `backtest.py`, dans la fonction `register_example_edges()` :

```python
def my_condition(df: pd.DataFrame) -> pd.Series:
    ...
    return signals

register_edge(Edge(
    name="Mon Edge",
    entry_condition=my_condition,
    close_horizons=[1, 6, 24],
))
```

## Exécution

```bash
python backtest.py                          # Tous les edges
python backtest.py --edge "Mon Edge"        # Edge spécifique
python backtest.py --list-edges             # Lister les edges
python backtest.py --since 2022-01-01       # Période personnalisée
```

Les rapports sont générés dans le dossier courant sous forme d'images PNG.
