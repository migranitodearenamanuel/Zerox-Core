import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Swing:
    low_idx: int
    low: float
    high_idx: int
    high: float
    direccion: str  # "ALCISTA" (low->high) o "BAJISTA" (high->low)


def detectar_swing_basico(df: pd.DataFrame, lookback: int = 60) -> Optional[Swing]:
    if df is None or len(df) < 30:
        return None

    n = min(int(lookback), len(df))
    sub = df.iloc[-n:]

    try:
        high = sub["high"].astype(float).values
        low = sub["low"].astype(float).values
    except Exception:
        return None

    idx_high_local = int(np.argmax(high))
    idx_low_local = int(np.argmin(low))

    high_price = float(high[idx_high_local])
    low_price = float(low[idx_low_local])

    # Map a índices globales en df
    offset = len(df) - n
    idx_high = offset + idx_high_local
    idx_low = offset + idx_low_local

    # Si el máximo ocurre después del mínimo, interpretamos un swing alcista (low->high)
    if idx_high > idx_low:
        return Swing(low_idx=idx_low, low=low_price, high_idx=idx_high, high=high_price, direccion="ALCISTA")
    return Swing(low_idx=idx_low, low=low_price, high_idx=idx_high, high=high_price, direccion="BAJISTA")


def niveles_retroceso(swing: Swing) -> Dict[str, float]:
    """
    Retorna niveles de retroceso clásicos: 0.236, 0.382, 0.5, 0.618, 0.786
    Para swing ALCISTA: niveles bajo el máximo (zonas de pullback).
    Para swing BAJISTA: niveles sobre el mínimo (rebotes).
    """
    r = float(swing.high - swing.low)
    if r <= 0:
        return {}

    ratios = [0.236, 0.382, 0.5, 0.618, 0.786]
    niveles = {}
    if swing.direccion == "ALCISTA":
        for k in ratios:
            niveles[f"{k:.3f}"] = swing.high - r * k
    else:
        for k in ratios:
            niveles[f"{k:.3f}"] = swing.low + r * k
    return niveles


def niveles_extension(swing: Swing) -> Dict[str, float]:
    """
    Extensiones simples: 1.272, 1.618, 2.000, 2.618
    """
    r = float(swing.high - swing.low)
    if r <= 0:
        return {}

    exts = [1.272, 1.618, 2.0, 2.618]
    niveles = {}
    if swing.direccion == "ALCISTA":
        for k in exts:
            niveles[f"EXT_{k:.3f}"] = swing.low + r * k
    else:
        for k in exts:
            niveles[f"EXT_{k:.3f}"] = swing.high - r * k
    return niveles


def nivel_cercano(precio: float, niveles: Dict[str, float], tolerancia_abs: float) -> Optional[Tuple[str, float, float]]:
    """
    Devuelve (nombre_nivel, precio_nivel, distancia_abs) del más cercano dentro de tolerancia.
    """
    try:
        precio = float(precio)
        tolerancia_abs = float(tolerancia_abs)
    except Exception:
        return None

    if tolerancia_abs <= 0 or not niveles:
        return None

    mejor = None
    for nombre, p in niveles.items():
        try:
            p = float(p)
        except Exception:
            continue
        d = abs(precio - p)
        if d <= tolerancia_abs and (mejor is None or d < mejor[2]):
            mejor = (nombre, p, d)
    return mejor


def tolerancia_por_atr(atr: float, multiplicador: float = 0.35, min_pct: float = 0.001) -> float:
    """
    Tolerancia absoluta para "estar cerca" de un nivel.
    - preferimos ATR, pero si ATR es 0 usamos un mínimo porcentual.
    """
    try:
        atr = float(atr)
    except Exception:
        atr = 0.0
    try:
        multiplicador = float(multiplicador)
    except Exception:
        multiplicador = 0.35
    try:
        min_pct = float(min_pct)
    except Exception:
        min_pct = 0.001

    if atr > 0:
        return atr * max(0.05, multiplicador)
    # fallback: se convierte a tolerancia "relativa" en el caller con precio
    return 0.0
