from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PatronDetectado:
    nombre: str
    direccion: str  # "LONG" o "SHORT"
    fuerza: float   # 0..1 (heurístico)
    detalle: Dict


def _pivotes(df: pd.DataFrame, ventana: int = 3) -> Tuple[List[int], List[int]]:
    """
    Retorna listas de índices (en df) de pivot highs y pivot lows.
    """
    if df is None or len(df) < (ventana * 2 + 10):
        return [], []

    ventana = int(max(2, ventana))
    highs = df["high"].astype(float).values
    lows = df["low"].astype(float).values

    piv_hi = []
    piv_lo = []
    for i in range(ventana, len(df) - ventana):
        h = highs[i]
        l = lows[i]
        if h == np.max(highs[i - ventana : i + ventana + 1]):
            piv_hi.append(i)
        if l == np.min(lows[i - ventana : i + ventana + 1]):
            piv_lo.append(i)

    return piv_hi, piv_lo


def _tolerancia(tol_abs: float, precio: float, tol_pct: float = 0.003) -> float:
    try:
        tol_abs = float(tol_abs)
    except Exception:
        tol_abs = 0.0
    if tol_abs > 0:
        return tol_abs
    try:
        precio = float(precio)
    except Exception:
        precio = 0.0
    return abs(precio) * float(tol_pct)


def detectar_doble_techo_suelo(df: pd.DataFrame, atr: float = 0.0, ventana_pivote: int = 3) -> Optional[PatronDetectado]:
    piv_hi, piv_lo = _pivotes(df, ventana=ventana_pivote)
    if len(piv_hi) < 2 and len(piv_lo) < 2:
        return None

    close = float(df["close"].iloc[-1])
    tol = _tolerancia(atr * 0.6, close, tol_pct=0.004)

    # --- Doble techo (SHORT) ---
    if len(piv_hi) >= 2:
        a, b = piv_hi[-2], piv_hi[-1]
        pa = float(df["high"].iloc[a])
        pb = float(df["high"].iloc[b])
        if abs(pa - pb) <= tol:
            # Neckline = mínimo entre a y b
            low_between = float(df["low"].iloc[min(a, b) : max(a, b) + 1].min())
            ruptura = close < low_between
            fuerza = 0.75 + (0.15 if ruptura else 0.0)
            return PatronDetectado(
                nombre="DOBLE_TECHO",
                direccion="SHORT",
                fuerza=min(1.0, fuerza),
                detalle={"pico1": pa, "pico2": pb, "neckline": low_between, "ruptura": ruptura},
            )

    # --- Doble suelo (LONG) ---
    if len(piv_lo) >= 2:
        a, b = piv_lo[-2], piv_lo[-1]
        pa = float(df["low"].iloc[a])
        pb = float(df["low"].iloc[b])
        if abs(pa - pb) <= tol:
            high_between = float(df["high"].iloc[min(a, b) : max(a, b) + 1].max())
            ruptura = close > high_between
            fuerza = 0.75 + (0.15 if ruptura else 0.0)
            return PatronDetectado(
                nombre="DOBLE_SUELO",
                direccion="LONG",
                fuerza=min(1.0, fuerza),
                detalle={"suelo1": pa, "suelo2": pb, "neckline": high_between, "ruptura": ruptura},
            )

    return None


def detectar_hch(df: pd.DataFrame, atr: float = 0.0, ventana_pivote: int = 3) -> Optional[PatronDetectado]:
    """
    Detección MVP:
    - HCH (SHORT): 3 pivot highs (LS, H, RS) con H más alto y hombros similares.
    - HCHi (LONG): 3 pivot lows (LS, H, RS) con H más bajo y hombros similares.
    """
    piv_hi, piv_lo = _pivotes(df, ventana=ventana_pivote)
    close = float(df["close"].iloc[-1])
    tol = _tolerancia(atr * 0.7, close, tol_pct=0.005)

    # HCH (SHORT)
    if len(piv_hi) >= 3:
        i1, i2, i3 = piv_hi[-3], piv_hi[-2], piv_hi[-1]
        p1 = float(df["high"].iloc[i1])
        p2 = float(df["high"].iloc[i2])
        p3 = float(df["high"].iloc[i3])
        hombros_similares = abs(p1 - p3) <= tol
        cabeza_mas_alta = p2 > p1 + tol * 0.5 and p2 > p3 + tol * 0.5
        if hombros_similares and cabeza_mas_alta:
            low_between_1 = float(df["low"].iloc[min(i1, i2) : max(i1, i2) + 1].min())
            low_between_2 = float(df["low"].iloc[min(i2, i3) : max(i2, i3) + 1].min())
            neckline = min(low_between_1, low_between_2)
            ruptura = close < neckline
            fuerza = 0.8 + (0.15 if ruptura else 0.0)
            return PatronDetectado(
                nombre="HCH",
                direccion="SHORT",
                fuerza=min(1.0, fuerza),
                detalle={"hombro_izq": p1, "cabeza": p2, "hombro_der": p3, "neckline": neckline, "ruptura": ruptura},
            )

    # HCH invertido (LONG)
    if len(piv_lo) >= 3:
        i1, i2, i3 = piv_lo[-3], piv_lo[-2], piv_lo[-1]
        p1 = float(df["low"].iloc[i1])
        p2 = float(df["low"].iloc[i2])
        p3 = float(df["low"].iloc[i3])
        hombros_similares = abs(p1 - p3) <= tol
        cabeza_mas_baja = p2 < p1 - tol * 0.5 and p2 < p3 - tol * 0.5
        if hombros_similares and cabeza_mas_baja:
            high_between_1 = float(df["high"].iloc[min(i1, i2) : max(i1, i2) + 1].max())
            high_between_2 = float(df["high"].iloc[min(i2, i3) : max(i2, i3) + 1].max())
            neckline = max(high_between_1, high_between_2)
            ruptura = close > neckline
            fuerza = 0.8 + (0.15 if ruptura else 0.0)
            return PatronDetectado(
                nombre="HCHi",
                direccion="LONG",
                fuerza=min(1.0, fuerza),
                detalle={"hombro_izq": p1, "cabeza": p2, "hombro_der": p3, "neckline": neckline, "ruptura": ruptura},
            )

    return None


def detectar_triangulo(df: pd.DataFrame, atr: float = 0.0, ventana_pivote: int = 3) -> Optional[PatronDetectado]:
    """
    Triángulo simétrico MVP:
    - 3 highs decrecientes y 3 lows crecientes.
    - Señal si hay ruptura (close > último high pivot o close < último low pivot).
    """
    piv_hi, piv_lo = _pivotes(df, ventana=ventana_pivote)
    if len(piv_hi) < 3 or len(piv_lo) < 3:
        return None

    hi_idx = piv_hi[-3:]
    lo_idx = piv_lo[-3:]

    hi_prices = [float(df["high"].iloc[i]) for i in hi_idx]
    lo_prices = [float(df["low"].iloc[i]) for i in lo_idx]

    highs_decrecientes = hi_prices[0] > hi_prices[1] and hi_prices[1] > hi_prices[2]
    lows_crecientes = lo_prices[0] < lo_prices[1] and lo_prices[1] < lo_prices[2]
    if not (highs_decrecientes and lows_crecientes):
        return None

    close = float(df["close"].iloc[-1])
    ultimo_hi = hi_prices[-1]
    ultimo_lo = lo_prices[-1]
    ruptura_arriba = close > ultimo_hi
    ruptura_abajo = close < ultimo_lo

    if ruptura_arriba:
        return PatronDetectado(
            nombre="TRIANGULO_SIMETRICO",
            direccion="LONG",
            fuerza=0.7 + 0.2,
            detalle={"highs": hi_prices, "lows": lo_prices, "ruptura": "ARRIBA"},
        )
    if ruptura_abajo:
        return PatronDetectado(
            nombre="TRIANGULO_SIMETRICO",
            direccion="SHORT",
            fuerza=0.7 + 0.2,
            detalle={"highs": hi_prices, "lows": lo_prices, "ruptura": "ABAJO"},
        )

    return PatronDetectado(
        nombre="TRIANGULO_SIMETRICO",
        direccion="ESPERAR",
        fuerza=0.55,
        detalle={"highs": hi_prices, "lows": lo_prices, "ruptura": False},
    )


def detectar_bandera_simple(df: pd.DataFrame, atr: float = 0.0) -> Optional[PatronDetectado]:
    """
    Bandera simple:
    - Impulso fuerte (rango > 2*ATR) en las últimas ~25 velas.
    - Consolidación corta (rango medio < 1*ATR).
    - Ruptura del máximo/mínimo de la consolidación.
    """
    if df is None or len(df) < 40:
        return None

    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)

    atr = float(atr or 0.0)
    if atr <= 0:
        return None

    ventana_impulso = df.iloc[-30:-10]
    rangos = (ventana_impulso["high"].astype(float) - ventana_impulso["low"].astype(float)).values
    if len(rangos) == 0:
        return None

    impulso = float(np.max(rangos))
    if impulso < 2.0 * atr:
        return None

    consolidacion = df.iloc[-10:]
    rango_med = float((consolidacion["high"].astype(float) - consolidacion["low"].astype(float)).mean())
    if rango_med > 1.0 * atr:
        return None

    max_cons = float(consolidacion["high"].max())
    min_cons = float(consolidacion["low"].min())
    c = float(close.iloc[-1])

    if c > max_cons:
        return PatronDetectado(
            nombre="BANDERA_ALCISTA",
            direccion="LONG",
            fuerza=0.75,
            detalle={"impulso": impulso, "rango_consolidacion": rango_med, "ruptura": "ARRIBA"},
        )
    if c < min_cons:
        return PatronDetectado(
            nombre="BANDERA_BAJISTA",
            direccion="SHORT",
            fuerza=0.75,
            detalle={"impulso": impulso, "rango_consolidacion": rango_med, "ruptura": "ABAJO"},
        )
    return None


def detectar_triple_techo_suelo(df: pd.DataFrame, atr: float = 0.0, ventana_pivote: int = 3) -> Optional[PatronDetectado]:
    """
    Triple techo / triple suelo (heurístico):
    - 3 pivot highs/lows "cercanos" dentro de una tolerancia.
    - Ruptura si el close rompe neckline.
    """
    piv_hi, piv_lo = _pivotes(df, ventana=ventana_pivote)
    if len(piv_hi) < 3 and len(piv_lo) < 3:
        return None

    close = float(df["close"].iloc[-1])
    tol = _tolerancia(atr * 0.65, close, tol_pct=0.004)

    # Triple techo (SHORT)
    if len(piv_hi) >= 3:
        a, b, c = piv_hi[-3], piv_hi[-2], piv_hi[-1]
        pa = float(df["high"].iloc[a])
        pb = float(df["high"].iloc[b])
        pc = float(df["high"].iloc[c])
        if max(pa, pb, pc) - min(pa, pb, pc) <= tol:
            low_between = float(df["low"].iloc[min(a, c) : max(a, c) + 1].min())
            ruptura = close < low_between
            fuerza = 0.78 + (0.15 if ruptura else 0.0)
            return PatronDetectado(
                nombre="TRIPLE_TECHO",
                direccion="SHORT",
                fuerza=min(1.0, fuerza),
                detalle={"picos": [pa, pb, pc], "neckline": low_between, "ruptura": ruptura},
            )

    # Triple suelo (LONG)
    if len(piv_lo) >= 3:
        a, b, c = piv_lo[-3], piv_lo[-2], piv_lo[-1]
        pa = float(df["low"].iloc[a])
        pb = float(df["low"].iloc[b])
        pc = float(df["low"].iloc[c])
        if max(pa, pb, pc) - min(pa, pb, pc) <= tol:
            high_between = float(df["high"].iloc[min(a, c) : max(a, c) + 1].max())
            ruptura = close > high_between
            fuerza = 0.78 + (0.15 if ruptura else 0.0)
            return PatronDetectado(
                nombre="TRIPLE_SUELO",
                direccion="LONG",
                fuerza=min(1.0, fuerza),
                detalle={"suelos": [pa, pb, pc], "neckline": high_between, "ruptura": ruptura},
            )

    return None


def detectar_triangulo_asc_desc(df: pd.DataFrame, atr: float = 0.0, ventana_pivote: int = 3) -> Optional[PatronDetectado]:
    """
    Triángulos ascendente/descendente (MVP):
    - Ascendente: highs ~ iguales + lows crecientes.
    - Descendente: lows ~ iguales + highs decrecientes.
    """
    piv_hi, piv_lo = _pivotes(df, ventana=ventana_pivote)
    if len(piv_hi) < 3 or len(piv_lo) < 3:
        return None

    close = float(df["close"].iloc[-1])
    tol = _tolerancia(atr * 0.55, close, tol_pct=0.004)

    hi_idx = piv_hi[-3:]
    lo_idx = piv_lo[-3:]
    hi_prices = [float(df["high"].iloc[i]) for i in hi_idx]
    lo_prices = [float(df["low"].iloc[i]) for i in lo_idx]

    highs_casi_iguales = (max(hi_prices) - min(hi_prices)) <= tol
    lows_casi_iguales = (max(lo_prices) - min(lo_prices)) <= tol

    lows_crecientes = lo_prices[0] < lo_prices[1] and lo_prices[1] < lo_prices[2]
    highs_decrecientes = hi_prices[0] > hi_prices[1] and hi_prices[1] > hi_prices[2]

    resistencia = float(np.mean(hi_prices))
    soporte = float(np.mean(lo_prices))

    if highs_casi_iguales and lows_crecientes:
        ruptura_arriba = close > resistencia
        ruptura_abajo = close < lo_prices[-1]
        if ruptura_arriba:
            return PatronDetectado("TRIANGULO_ASCENDENTE", "LONG", 0.78, {"resistencia": resistencia, "lows": lo_prices, "ruptura": "ARRIBA"})
        if ruptura_abajo:
            return PatronDetectado("TRIANGULO_ASCENDENTE", "SHORT", 0.70, {"resistencia": resistencia, "lows": lo_prices, "ruptura": "ABAJO"})
        return PatronDetectado("TRIANGULO_ASCENDENTE", "ESPERAR", 0.55, {"resistencia": resistencia, "lows": lo_prices, "ruptura": False})

    if lows_casi_iguales and highs_decrecientes:
        ruptura_abajo = close < soporte
        ruptura_arriba = close > hi_prices[-1]
        if ruptura_abajo:
            return PatronDetectado("TRIANGULO_DESCENDENTE", "SHORT", 0.78, {"soporte": soporte, "highs": hi_prices, "ruptura": "ABAJO"})
        if ruptura_arriba:
            return PatronDetectado("TRIANGULO_DESCENDENTE", "LONG", 0.70, {"soporte": soporte, "highs": hi_prices, "ruptura": "ARRIBA"})
        return PatronDetectado("TRIANGULO_DESCENDENTE", "ESPERAR", 0.55, {"soporte": soporte, "highs": hi_prices, "ruptura": False})

    return None


def detectar_rectangulo(df: pd.DataFrame, atr: float = 0.0, ventana_pivote: int = 3) -> Optional[PatronDetectado]:
    """
    Rectángulo/rango (MVP):
    - highs ~ iguales y lows ~ iguales.
    - Señal solo si hay ruptura.
    """
    piv_hi, piv_lo = _pivotes(df, ventana=ventana_pivote)
    if len(piv_hi) < 2 or len(piv_lo) < 2:
        return None

    close = float(df["close"].iloc[-1])
    tol = _tolerancia(atr * 0.55, close, tol_pct=0.004)

    hi_idx = piv_hi[-2:]
    lo_idx = piv_lo[-2:]
    hi_prices = [float(df["high"].iloc[i]) for i in hi_idx]
    lo_prices = [float(df["low"].iloc[i]) for i in lo_idx]

    highs_ok = (max(hi_prices) - min(hi_prices)) <= tol
    lows_ok = (max(lo_prices) - min(lo_prices)) <= tol
    if not (highs_ok and lows_ok):
        return None

    rango_alto = float(np.mean(hi_prices))
    rango_bajo = float(np.mean(lo_prices))
    if rango_bajo <= 0 or rango_alto <= rango_bajo:
        return None

    if close > rango_alto:
        return PatronDetectado("RECTANGULO", "LONG", 0.72, {"rango_alto": rango_alto, "rango_bajo": rango_bajo, "ruptura": "ARRIBA"})
    if close < rango_bajo:
        return PatronDetectado("RECTANGULO", "SHORT", 0.72, {"rango_alto": rango_alto, "rango_bajo": rango_bajo, "ruptura": "ABAJO"})
    return PatronDetectado("RECTANGULO", "ESPERAR", 0.50, {"rango_alto": rango_alto, "rango_bajo": rango_bajo, "ruptura": False})


def detectar_cuna(df: pd.DataFrame, atr: float = 0.0, ventana_pivote: int = 3) -> Optional[PatronDetectado]:
    """
    Cuña (wedge) simplificada:
    - Rising wedge: highs y lows suben, pero el rango se estrecha => sesgo bajista.
    - Falling wedge: highs y lows bajan, rango se estrecha => sesgo alcista.
    """
    piv_hi, piv_lo = _pivotes(df, ventana=ventana_pivote)
    if len(piv_hi) < 3 or len(piv_lo) < 3:
        return None

    hi_idx = piv_hi[-3:]
    lo_idx = piv_lo[-3:]
    hi_prices = [float(df["high"].iloc[i]) for i in hi_idx]
    lo_prices = [float(df["low"].iloc[i]) for i in lo_idx]

    rango_0 = hi_prices[0] - lo_prices[0]
    rango_2 = hi_prices[-1] - lo_prices[-1]
    if rango_0 <= 0:
        return None

    estrecha = rango_2 < (rango_0 * 0.85)
    close = float(df["close"].iloc[-1])

    highs_suben = hi_prices[0] < hi_prices[1] < hi_prices[2]
    lows_suben = lo_prices[0] < lo_prices[1] < lo_prices[2]
    highs_bajan = hi_prices[0] > hi_prices[1] > hi_prices[2]
    lows_bajan = lo_prices[0] > lo_prices[1] > lo_prices[2]

    if estrecha and highs_suben and lows_suben:
        ruptura = close < lo_prices[-1]
        fuerza = 0.62 + (0.20 if ruptura else 0.0)
        return PatronDetectado("CUÑA_ALCISTA", "SHORT" if ruptura else "ESPERAR", min(1.0, fuerza), {"highs": hi_prices, "lows": lo_prices, "ruptura": "ABAJO" if ruptura else False})

    if estrecha and highs_bajan and lows_bajan:
        ruptura = close > hi_prices[-1]
        fuerza = 0.62 + (0.20 if ruptura else 0.0)
        return PatronDetectado("CUÑA_BAJISTA", "LONG" if ruptura else "ESPERAR", min(1.0, fuerza), {"highs": hi_prices, "lows": lo_prices, "ruptura": "ARRIBA" if ruptura else False})

    return None


def detectar_patron(df: pd.DataFrame, atr: float = 0.0) -> Optional[PatronDetectado]:
    candidatos: List[PatronDetectado] = []
    for detector in (
        detectar_hch,
        detectar_triple_techo_suelo,
        detectar_doble_techo_suelo,
        detectar_triangulo_asc_desc,
        detectar_triangulo,
        detectar_rectangulo,
        detectar_cuna,
        detectar_bandera_simple,
    ):
        try:
            patron = detector(df, atr=atr)
            if patron is not None:
                candidatos.append(patron)
        except Exception:
            continue

    if not candidatos:
        return None

    # Preferir: fuerza alta y dirección accionable (LONG/SHORT) sobre "ESPERAR"
    def _rank(p: PatronDetectado) -> float:
        bonus = 0.08 if p.direccion in ("LONG", "SHORT") else 0.0
        return float(p.fuerza) + bonus

    candidatos.sort(key=_rank, reverse=True)
    return candidatos[0]
