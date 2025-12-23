from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from . import fibonacci
from . import indicadores
from . import patrones_chartistas


def _clamp(x: float, a: float, b: float) -> float:
    try:
        x = float(x)
    except Exception:
        x = 0.0
    return max(a, min(b, x))


def _decimales_por_precio(precio: float) -> int:
    try:
        p = float(precio)
    except Exception:
        return 2
    if p < 0.01:
        return 7
    if p < 1:
        return 5
    if p < 100:
        return 3
    return 2


def _rr_dinamico(conf: float, adx: float, atr_pct: float) -> float:
    """
    RR dinámico en [1.2, 5.0] según confianza y régimen.
    """
    base = 1.2
    if conf >= 85:
        base = 3.0
    elif conf >= 75:
        base = 2.2
    elif conf >= 65:
        base = 1.7
    else:
        base = 1.3

    if adx >= 25:
        base *= 1.15

    if atr_pct >= 3.0:
        base *= 0.90

    return _clamp(base, 1.2, 5.0)


def _sl_por_estructura(df: pd.DataFrame, direccion: str, precio: float, atr: float) -> Optional[Dict[str, float]]:
    """
    SL por estructura (swing) + buffer ATR.
    """
    if df is None or len(df) < 30:
        return None

    direccion = str(direccion).upper()
    precio = float(precio)
    atr = float(atr or 0.0)

    sub = df.iloc[-50:] if len(df) >= 50 else df
    swing_low = float(sub["low"].astype(float).min())
    swing_high = float(sub["high"].astype(float).max())

    buffer = max(atr * 0.35, precio * 0.0015)  # ATR o ~0.15% del precio

    if direccion == "LONG":
        sl = swing_low - buffer
        if sl >= precio:
            sl = precio * (1.0 - 0.003)
    else:
        sl = swing_high + buffer
        if sl <= precio:
            sl = precio * (1.0 + 0.003)

    return {"sl": float(sl), "swing_low": swing_low, "swing_high": swing_high, "buffer": buffer}


def _detectar_divergencia_rsi(
    df: pd.DataFrame,
    rsi_series: pd.Series,
    ventana_pivote: int = 3,
    min_delta_rsi: float = 2.0,
) -> Optional[Dict[str, Any]]:
    """
    Divergencias RSI (MVP determinista):
    - Alcista: precio hace mínimo más bajo y RSI hace mínimo más alto.
    - Bajista: precio hace máximo más alto y RSI hace máximo más bajo.
    """
    try:
        piv_hi, piv_lo = patrones_chartistas._pivotes(df, ventana=int(ventana_pivote))
    except Exception:
        return None

    try:
        min_delta_rsi = float(min_delta_rsi)
    except Exception:
        min_delta_rsi = 2.0

    # Alcista (pivotes low)
    if len(piv_lo) >= 2:
        i1, i2 = piv_lo[-2], piv_lo[-1]
        p1 = float(df["low"].iloc[i1])
        p2 = float(df["low"].iloc[i2])
        r1 = float(rsi_series.iloc[i1])
        r2 = float(rsi_series.iloc[i2])
        if p2 < p1 and r2 > (r1 + min_delta_rsi):
            return {
                "tipo": "ALCISTA",
                "precio": {"p1": p1, "p2": p2, "idx": [i1, i2]},
                "rsi": {"r1": r1, "r2": r2},
            }

    # Bajista (pivotes high)
    if len(piv_hi) >= 2:
        i1, i2 = piv_hi[-2], piv_hi[-1]
        p1 = float(df["high"].iloc[i1])
        p2 = float(df["high"].iloc[i2])
        r1 = float(rsi_series.iloc[i1])
        r2 = float(rsi_series.iloc[i2])
        if p2 > p1 and r2 < (r1 - min_delta_rsi):
            return {
                "tipo": "BAJISTA",
                "precio": {"p1": p1, "p2": p2, "idx": [i1, i2]},
                "rsi": {"r1": r1, "r2": r2},
            }

    return None


def evaluar_setup_determinista(df: pd.DataFrame, simbolo: str = "", temporalidad: str = "") -> Dict[str, Any]:
    """
    Motor de señales determinista + scoring por confluencias.

    Devuelve (además de campos legacy usados por el core):
    {
      "setup": bool,
      "lado": "LONG|SHORT|ESPERAR",
      "score": 0-100,
      "razones": [...],
      "confluencias": [...],
      "invalidaciones": [...]
    }
    """
    if df is None or len(df) < 50:
        razones = ["Datos insuficientes para análisis técnico determinista."]
        return {
            "setup": False,
            "lado": "ESPERAR",
            "score": 0,
            "razones": razones,
            "confluencias": [],
            "invalidaciones": ["DATOS_INSUFICIENTES"],
            # legacy
            "decision": "ESPERAR",
            "confianza": 0,
            "razon": razones[0],
            "detalle_setup": {"patron": None, "fibo": None, "divergencias": None, "indicadores": {}, "volumen": None},
            "plan": {"sl": None, "tp": None, "rr": None, "apalancamiento_sugerido": 1},
            "meta": {"simbolo": simbolo, "temporalidad": temporalidad, "scores": {"long": 0, "short": 0}},
        }

    precio = float(df["close"].iloc[-1])
    decs = _decimales_por_precio(precio)

    rsi_series = indicadores.rsi(df["close"].astype(float), periodo=14)
    rsi_val = float(rsi_series.iloc[-1])
    ema_fast = float(indicadores.ema(df["close"].astype(float), 20).iloc[-1])
    ema_slow = float(indicadores.ema(df["close"].astype(float), 50).iloc[-1])
    macd_line, macd_sig, macd_hist = indicadores.macd(df["close"].astype(float))
    macd_val = float(macd_line.iloc[-1])
    macd_sig_val = float(macd_sig.iloc[-1])
    macd_hist_val = float(macd_hist.iloc[-1])
    atr_series = indicadores.atr(df, periodo=14)
    atr_val = float(atr_series.iloc[-1]) if len(atr_series) else 0.0
    adx_series = indicadores.adx(df, periodo=14)
    adx_val = float(adx_series.iloc[-1]) if len(adx_series) else 0.0
    vwap_series = indicadores.vwap(df)
    vwap_val = float(vwap_series.iloc[-1]) if len(vwap_series) else precio
    vol_ratio = float(indicadores.volumen_ratio(df, periodo=20))

    atr_pct = (atr_val / precio * 100) if precio > 0 else 0.0

    tendencia_alcista = ema_fast > ema_slow
    tendencia_bajista = ema_fast < ema_slow

    # --- Patrones ---
    patron = patrones_chartistas.detectar_patron(df, atr=atr_val)

    # --- Fibonacci ---
    swing = fibonacci.detectar_swing_basico(df, lookback=60)
    fibo_info = None
    if swing is not None and atr_val > 0:
        retro = fibonacci.niveles_retroceso(swing)
        tol_abs = fibonacci.tolerancia_por_atr(atr_val, multiplicador=0.35, min_pct=0.001)
        if tol_abs <= 0:
            tol_abs = precio * 0.0015
        nivel = fibonacci.nivel_cercano(precio, retro, tolerancia_abs=tol_abs)
        if nivel is not None:
            fibo_info = {"nivel": nivel[0], "precio": float(nivel[1]), "direccion_swing": swing.direccion}

    # --- Divergencias RSI ---
    divergencia = _detectar_divergencia_rsi(df, rsi_series, ventana_pivote=3, min_delta_rsi=2.0)

    # --- Scoring ---
    long_score = 50.0
    short_score = 50.0
    razones_long: List[str] = []
    razones_short: List[str] = []
    conf_long: List[str] = []
    conf_short: List[str] = []
    invalidaciones: List[str] = []

    # Tendencia (EMA)
    if tendencia_alcista:
        long_score += 15
        razones_long.append("Tendencia alcista (EMA20>EMA50)")
        conf_long.append("EMA")
    if tendencia_bajista:
        short_score += 15
        razones_short.append("Tendencia bajista (EMA20<EMA50)")
        conf_short.append("EMA")

    # MACD
    if macd_hist_val > 0 and macd_val > macd_sig_val:
        long_score += 12
        razones_long.append("MACD alcista (hist>0)")
        conf_long.append("MACD")
    if macd_hist_val < 0 and macd_val < macd_sig_val:
        short_score += 12
        razones_short.append("MACD bajista (hist<0)")
        conf_short.append("MACD")

    # RSI (extremos)
    if rsi_val <= 35:
        long_score += 6
        razones_long.append(f"RSI sobreventa ({rsi_val:.1f})")
    if rsi_val >= 65:
        short_score += 6
        razones_short.append(f"RSI sobrecompra ({rsi_val:.1f})")

    # RSI divergencias
    if divergencia and divergencia.get("tipo") == "ALCISTA":
        long_score += 10
        razones_long.append("Divergencia RSI alcista")
        conf_long.append("DIVERGENCIA_RSI")
    if divergencia and divergencia.get("tipo") == "BAJISTA":
        short_score += 10
        razones_short.append("Divergencia RSI bajista")
        conf_short.append("DIVERGENCIA_RSI")

    # ADX (tendencia fuerte)
    if adx_val >= 25:
        if tendencia_alcista:
            long_score += 4
            razones_long.append(f"ADX fuerte ({adx_val:.1f})")
        if tendencia_bajista:
            short_score += 4
            razones_short.append(f"ADX fuerte ({adx_val:.1f})")

    # VWAP (sesgo)
    if precio > vwap_val:
        long_score += 3
        razones_long.append("Precio sobre VWAP")
    if precio < vwap_val:
        short_score += 3
        razones_short.append("Precio bajo VWAP")

    # Volumen (confirmación)
    if vol_ratio >= 1.5:
        if tendencia_alcista:
            long_score += 8
            razones_long.append(f"Volumen de ruptura ({vol_ratio:.2f}x)")
            conf_long.append("VOLUMEN")
        if tendencia_bajista:
            short_score += 8
            razones_short.append(f"Volumen de ruptura ({vol_ratio:.2f}x)")
            conf_short.append("VOLUMEN")

    # Patrón chartista
    if patron is not None:
        if patron.direccion == "LONG":
            long_score += 25 * float(patron.fuerza)
            razones_long.append(f"Patrón {patron.nombre}")
            conf_long.append("PATRON")
        elif patron.direccion == "SHORT":
            short_score += 25 * float(patron.fuerza)
            razones_short.append(f"Patrón {patron.nombre}")
            conf_short.append("PATRON")
        else:
            long_score += 6 * float(patron.fuerza)
            short_score += 6 * float(patron.fuerza)

    # Fibonacci confluencia (solo si hay nivel cerca)
    if fibo_info is not None:
        if str(fibo_info.get("direccion_swing")) == "ALCISTA":
            long_score += 12
            razones_long.append(f"Confluencia Fibonacci {fibo_info['nivel']}")
            conf_long.append("FIBONACCI")
        elif str(fibo_info.get("direccion_swing")) == "BAJISTA":
            short_score += 12
            razones_short.append(f"Confluencia Fibonacci {fibo_info['nivel']}")
            conf_short.append("FIBONACCI")

    long_score = _clamp(long_score, 0, 100)
    short_score = _clamp(short_score, 0, 100)

    # --- Decisión base ---
    decision = "ESPERAR"
    conf = 0.0
    direccion = None
    if max(long_score, short_score) >= 60 and abs(long_score - short_score) >= 6:
        if long_score > short_score:
            decision = "COMPRA"
            conf = long_score
            direccion = "LONG"
        else:
            decision = "VENTA"
            conf = short_score
            direccion = "SHORT"

    # --- Plan (SL/TP/RR/Leverage sugerido) ---
    sl = None
    tp = None
    rr = None
    leverage_sugerido = 1
    estructura = None

    if direccion in ("LONG", "SHORT") and precio > 0:
        estructura = _sl_por_estructura(df, direccion, precio, atr_val)
        if estructura is None:
            invalidaciones.append("SL_INCALCULABLE")
        else:
            sl = float(estructura["sl"])
            sl_dist = abs(precio - sl)
            sl_dist_pct = (sl_dist / precio * 100) if precio > 0 else 0.0
            rr = _rr_dinamico(conf, adx_val, atr_pct)
            tp = precio + sl_dist * rr if direccion == "LONG" else precio - sl_dist * rr

            # Ajuste por extensiones fibo (si encaja)
            if swing is not None and atr_val > 0 and tp is not None:
                exts = fibonacci.niveles_extension(swing)
                tol_abs = max(atr_val * 0.5, precio * 0.002)
                nivel_ext = fibonacci.nivel_cercano(tp, exts, tolerancia_abs=tol_abs)
                if nivel_ext is not None:
                    tp = float(nivel_ext[1])

            # Leverage sugerido (luego se valida en gestor_riesgo)
            if sl_dist_pct > 0:
                l_max_liq = int(math.floor(0.80 / (sl_dist_pct / 100.0)))
            else:
                l_max_liq = 1

            l_base = 3
            if conf >= 85:
                l_base = 20
            elif conf >= 75:
                l_base = 10
            elif conf >= 65:
                l_base = 5

            leverage_sugerido = int(max(1, min(l_base, max(1, l_max_liq))))

    # Si no hay TP/SL => NO entra (forzamos ESPERAR)
    setup_ok = bool(decision in ("COMPRA", "VENTA") and sl is not None and tp is not None)
    if decision in ("COMPRA", "VENTA") and not setup_ok:
        decision = "ESPERAR"
        conf = 0.0
        direccion = None
        invalidaciones.append("SIN_TP_SL")

    # --- Razones finales ---
    if decision == "COMPRA":
        razones = razones_long
        confluencias = list(dict.fromkeys(conf_long))
    elif decision == "VENTA":
        razones = razones_short
        confluencias = list(dict.fromkeys(conf_short))
    else:
        razones = []
        if long_score >= 55:
            razones.append("Señal LONG parcial (sin confluencia suficiente)")
        if short_score >= 55:
            razones.append("Señal SHORT parcial (sin confluencia suficiente)")
        if not razones:
            razones.append("Sin confluencia suficiente (esperar)")
        confluencias = []

    razon_txt = " | ".join(razones)

    out = {
        # NUEVO (requerido)
        "setup": bool(decision in ("COMPRA", "VENTA") and setup_ok),
        "lado": "LONG" if decision == "COMPRA" else ("SHORT" if decision == "VENTA" else "ESPERAR"),
        "score": int(round(max(long_score, short_score))),
        "razones": razones,
        "confluencias": confluencias,
        "invalidaciones": invalidaciones,
        # LEGACY (para compatibilidad con el core actual)
        "decision": decision,
        "confianza": int(round(conf)) if decision in ("COMPRA", "VENTA") else 0,
        "razon": razon_txt,
        "detalle_setup": {
            "patron": patron.nombre if patron is not None else None,
            "fibo": fibo_info,
            "divergencias": divergencia,
            "indicadores": {
                "rsi": round(rsi_val, 2),
                "macd": round(macd_val, 6),
                "macd_signal": round(macd_sig_val, 6),
                "macd_hist": round(macd_hist_val, 6),
                "atr": round(atr_val, decs),
                "adx": round(adx_val, 2),
                "ema_fast": round(ema_fast, decs),
                "ema_slow": round(ema_slow, decs),
                "vwap": round(vwap_val, decs),
            },
            "volumen": {"breakout": bool(vol_ratio >= 1.5), "ratio": round(vol_ratio, 2)} if vol_ratio else None,
        },
        "plan": {
            "sl": round(sl, decs) if sl is not None else None,
            "tp": round(tp, decs) if tp is not None else None,
            "rr": round(rr, 2) if rr is not None else None,
            "apalancamiento_sugerido": int(leverage_sugerido),
        },
        "meta": {
            "simbolo": simbolo,
            "temporalidad": temporalidad,
            "scores": {"long": int(round(long_score)), "short": int(round(short_score))},
        },
    }
    return out

