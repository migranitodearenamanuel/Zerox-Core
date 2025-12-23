import json
import os
from typing import Any, Dict, Optional, Tuple

import pandas as pd

RUTA_BLACKLIST = os.path.join(os.path.dirname(__file__), "simbolos_bloqueados.json")
RUTA_PARAMETROS_ACTIVOS = os.path.join(os.path.dirname(__file__), "parametros_activos.json")


def _cargar_parametros_activos() -> Dict[str, Any]:
    defaults: Dict[str, Any] = {
        "tpsl": {
            "rr_min": 1.2,
            "rr_max": 5.0,
            # Si se define (p.ej. 2.0), usa RR fijo en vez de RR dinámico.
            "rr_objetivo": None,
        }
    }
    try:
        if os.path.exists(RUTA_PARAMETROS_ACTIVOS):
            with open(RUTA_PARAMETROS_ACTIVOS, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
                if isinstance(data, dict):
                    out = dict(defaults)
                    out.update(data)
                    tpsl_cfg = dict((defaults.get("tpsl") or {}) if isinstance(defaults.get("tpsl"), dict) else {})
                    if isinstance(data.get("tpsl"), dict):
                        tpsl_cfg.update(data.get("tpsl") or {})
                    out["tpsl"] = tpsl_cfg
                    return out
    except Exception:
        return defaults
    return defaults


def _cargar_blacklist() -> Dict[str, Any]:
    try:
        if os.path.exists(RUTA_BLACKLIST):
            with open(RUTA_BLACKLIST, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}


def _es_simbolo_en_cuarentena(simbolo: str, blacklist: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    if not simbolo or not isinstance(simbolo, str) or not blacklist:
        return False, None

    simbolo_normalizado = simbolo.split(":")[0]
    base = simbolo_normalizado.split("/")[0].strip() if "/" in simbolo_normalizado else simbolo_normalizado.strip()
    if not base:
        return False, None

    for key in (f"{base}USDT_UMCBL", f"{base}USDT"):
        if key in blacklist:
            return True, key

    pref = f"{base}USDT"
    for key in blacklist.keys():
        if isinstance(key, str) and key.startswith(pref):
            return True, key

    return False, None


def _decimales_por_precio(simbolo: str, precio: float) -> int:
    try:
        precio = float(precio)
    except Exception:
        precio = 0.0

    if simbolo and any(x in simbolo for x in ("PEPE", "SHIB")):
        return 7
    if precio < 0.01:
        return 7
    if precio < 1.0:
        return 5
    if precio < 100:
        return 3
    return 2


def _rr_dinamico(confianza: float, atr_pct: float) -> float:
    """
    RR dinámico en rango [1.2, 5.0]:
    - Sube con confianza.
    - Baja con volatilidad extrema (ATR% alto).
    """
    try:
        c = float(confianza)
    except Exception:
        c = 0.0

    if c >= 90:
        rr = 3.5
    elif c >= 85:
        rr = 3.0
    elif c >= 75:
        rr = 2.2
    elif c >= 65:
        rr = 1.7
    else:
        rr = 1.2

    try:
        atr_pct = float(atr_pct)
    except Exception:
        atr_pct = 0.0

    if atr_pct >= 3.0:
        rr *= 0.90
    if atr_pct >= 5.0:
        rr *= 0.85

    return float(max(1.2, min(5.0, rr)))


def _sl_por_estructura(
    df: Optional[pd.DataFrame],
    direccion: str,
    precio_entrada: float,
    atr: float,
) -> Tuple[Optional[float], Dict[str, Any]]:
    """
    SL por estructura (swing low/high) + buffer ATR.
    """
    info: Dict[str, Any] = {}
    if df is None or len(df) < 30:
        return None, info

    direccion = str(direccion).upper()
    try:
        pe = float(precio_entrada)
    except Exception:
        return None, info

    try:
        atr = float(atr or 0.0)
    except Exception:
        atr = 0.0

    sub = df.iloc[-50:] if len(df) >= 50 else df
    try:
        swing_low = float(sub["low"].astype(float).min())
        swing_high = float(sub["high"].astype(float).max())
    except Exception:
        return None, info

    buffer = max(atr * 0.35, pe * 0.0015)  # ATR o ~0.15%

    if direccion == "LONG":
        sl = swing_low - buffer
    else:
        sl = swing_high + buffer

    info.update({"swing_low": swing_low, "swing_high": swing_high, "buffer": buffer})
    return float(sl), info


def _tp_por_rr_y_confluencia(
    df: Optional[pd.DataFrame],
    direccion: str,
    precio_entrada: float,
    sl: float,
    rr: float,
    rr_min: float = 1.2,
    rr_max: float = 5.0,
) -> Tuple[Optional[float], Dict[str, Any]]:
    """
    TP por RR mínimo + (si existe) extensión Fibonacci o resistencia/soporte cercano.

    MVP:
    - Usa extremos últimos 50 como estructura.
    - Usa extensiones simples 1.272/1.618/2.0 a partir del swing range.
    """
    info: Dict[str, Any] = {}
    direccion = str(direccion).upper()
    pe = float(precio_entrada)
    sl = float(sl)
    rr = float(rr)

    dist = abs(pe - sl)
    if dist <= 0:
        return None, info

    tp_rr = pe + dist * rr if direccion == "LONG" else pe - dist * rr
    candidatos = []

    if df is not None and len(df) >= 30:
        sub = df.iloc[-50:] if len(df) >= 50 else df
        try:
            swing_low = float(sub["low"].astype(float).min())
            swing_high = float(sub["high"].astype(float).max())
            r = float(swing_high - swing_low)
            if r > 0:
                if direccion == "LONG":
                    # resistencia obvia (máximo de la ventana)
                    if swing_high > pe:
                        candidatos.append(swing_high)
                    # extensiones por encima del swing_high
                    for k in (1.272, 1.618, 2.0, 2.618):
                        candidatos.append(swing_low + r * k)
                else:
                    if swing_low < pe:
                        candidatos.append(swing_low)
                    for k in (1.272, 1.618, 2.0, 2.618):
                        candidatos.append(swing_high - r * k)
        except Exception:
            pass

    # Respetar RR mínimo/máximo
    tp_min = pe + dist * rr_min if direccion == "LONG" else pe - dist * rr_min
    tp_max = pe + dist * rr_max if direccion == "LONG" else pe - dist * rr_max

    def _en_rango(x: float) -> bool:
        if direccion == "LONG":
            return x >= tp_min and x <= tp_max and x > pe
        return x <= tp_min and x >= tp_max and x < pe

    candidatos_validos = [float(x) for x in candidatos if _en_rango(float(x))]
    if candidatos_validos:
        elegido = min(candidatos_validos, key=lambda x: abs(x - tp_rr))
        info["tp_confluencia"] = float(elegido)
        return float(elegido), info

    return float(tp_rr), info


def calcular_plan_tpsl_profesional(
    simbolo: str,
    direccion: str,
    precio_entrada: float,
    atr: float,
    confianza: float,
    df: Optional[pd.DataFrame] = None,
    habilitar_tp_parciales: bool = False,
    rr_mult: float = 1.0,
) -> Dict[str, Any]:
    """
    Plan profesional:
    - SL por estructura (swing low/high) + buffer ATR.
    - TP por RR dinámico + (si existe) confluencia por extensión/resistencia/soporte.
    - RR dinámico en [1.2, 5.0].

    Importante:
    - La colocación real en Bitget sigue siendo 1 TP + 1 SL (por ahora).
    - Los TP parciales se devuelven solo como plan (sin ejecutar automáticamente).
    """
    # Cuarentena
    blacklist = _cargar_blacklist()
    en_cuarentena, _ = _es_simbolo_en_cuarentena(simbolo, blacklist)
    if en_cuarentena:
        return {"tp": None, "sl": None, "rr": None, "tp_parciales": None, "motivo": "CUARENTENA_API"}

    try:
        pe = float(precio_entrada)
    except Exception:
        return {"tp": None, "sl": None, "rr": None, "tp_parciales": None, "motivo": "PRECIO_INVALIDO"}
    if pe <= 0:
        return {"tp": None, "sl": None, "rr": None, "tp_parciales": None, "motivo": "PRECIO_INVALIDO"}

    try:
        atr = float(atr or 0.0)
    except Exception:
        atr = 0.0
    try:
        conf = float(confianza)
    except Exception:
        conf = 0.0

    params_activos = _cargar_parametros_activos()
    tpsl_cfg = (params_activos.get("tpsl") or {}) if isinstance(params_activos.get("tpsl"), dict) else {}

    rr_min_cfg = tpsl_cfg.get("rr_min", 1.2)
    rr_max_cfg = tpsl_cfg.get("rr_max", 5.0)
    rr_objetivo_cfg = tpsl_cfg.get("rr_objetivo", None)

    try:
        rr_min = float(rr_min_cfg)
    except Exception:
        rr_min = 1.2
    try:
        rr_max = float(rr_max_cfg)
    except Exception:
        rr_max = 5.0
    rr_min = float(max(0.8, min(10.0, rr_min)))
    rr_max = float(max(rr_min, min(10.0, rr_max)))

    atr_pct = (atr / pe * 100) if pe > 0 and atr > 0 else 0.0
    rr_base = None
    try:
        if rr_objetivo_cfg is not None and rr_objetivo_cfg != "":
            rr_base = float(rr_objetivo_cfg)
    except Exception:
        rr_base = None

    rr = float(rr_base) if (rr_base is not None and rr_base > 0) else _rr_dinamico(conf, atr_pct=atr_pct)
    try:
        rr_mult = float(rr_mult or 1.0)
    except Exception:
        rr_mult = 1.0
    rr = float(max(rr_min, min(rr_max, rr * rr_mult)))

    # 1) SL por estructura + buffer ATR
    sl_info: Dict[str, Any] = {}
    sl, sl_info = _sl_por_estructura(df=df, direccion=direccion, precio_entrada=pe, atr=atr)

    # Fallback si no hay df suficiente
    if sl is None:
        if atr <= 0:
            distancia = pe * 0.015  # 1.5% base
        else:
            if conf >= 85:
                k = 1.0
            elif conf >= 70:
                k = 1.5
            elif conf >= 60:
                k = 2.0
            else:
                k = 2.5
            distancia = atr * k

        if str(direccion).upper() == "LONG":
            sl = pe - distancia
        else:
            sl = pe + distancia

    # 2) Hard limits de distancia SL (min 0.3% / max 3.5%)
    dist_sl = abs(pe - float(sl))
    dist_pct = (dist_sl / pe) * 100 if pe > 0 else 0.0

    if dist_pct < 0.3:
        # Ensanchar SL (reduce tamaño por riesgo, pero evita barridas por ruido)
        dist_sl = pe * 0.003
        sl = pe - dist_sl if str(direccion).upper() == "LONG" else pe + dist_sl
        dist_pct = 0.3

    if dist_pct > 20.0:
        # Limitamos al 20% como máximo absoluto para no rechazar trades en alta volatilidad (Memecoins)
        # El sizing se encargará de reducir la posición acorde.
        dist_sl = pe * 0.20
        sl = pe - dist_sl if str(direccion).upper() == "LONG" else pe + dist_sl
        dist_pct = 20.0
        # return {"tp": None, "sl": None, "rr": None, "tp_parciales": None, "motivo": "SL_DEMASIADO_LEJANO"}

    # 3) TP por RR + confluencia
    tp, tp_info = _tp_por_rr_y_confluencia(
        df=df,
        direccion=direccion,
        precio_entrada=pe,
        sl=float(sl),
        rr=rr,
        rr_min=rr_min,
        rr_max=rr_max,
    )
    if tp is None:
        return {"tp": None, "sl": None, "rr": None, "tp_parciales": None, "motivo": "TP_INVALIDO"}

    # 4) Validación final anti-suicidio
    dir_up = str(direccion).upper()
    if dir_up == "LONG" and (float(sl) >= pe or float(tp) <= pe):
        return {"tp": None, "sl": None, "rr": None, "tp_parciales": None, "motivo": "NIVELES_INVALIDOS"}
    if dir_up == "SHORT" and (float(sl) <= pe or float(tp) >= pe):
        return {"tp": None, "sl": None, "rr": None, "tp_parciales": None, "motivo": "NIVELES_INVALIDOS"}

    # 5) Redondeo
    dec = _decimales_por_precio(simbolo, pe)
    tp = round(float(tp), dec)
    sl = round(float(sl), dec)

    # 6) TP parciales (plan, no ejecución automática)
    tp_parciales = None
    if habilitar_tp_parciales:
        r1, r2, r3 = 1.0, 2.0, 3.0
        if dir_up == "LONG":
            tp1 = round(pe + dist_sl * r1, dec)
            tp2 = round(pe + dist_sl * r2, dec)
            tp3 = round(pe + dist_sl * r3, dec)
        else:
            tp1 = round(pe - dist_sl * r1, dec)
            tp2 = round(pe - dist_sl * r2, dec)
            tp3 = round(pe - dist_sl * r3, dec)
        tp_parciales = [
            {"tp": tp1, "porcentaje": 50, "rr": r1},
            {"tp": tp2, "porcentaje": 30, "rr": r2},
            {"tp": tp3, "porcentaje": 20, "rr": r3},
        ]

    return {
        "tp": tp,
        "sl": sl,
        "rr": float(round(rr, 2)),
        "tp_parciales": tp_parciales,
        "motivo": "OK",
        "detalle": {"sl": sl_info, "tp": tp_info, "atr_pct": round(float(atr_pct), 3)},
    }


def calcular_tpsl_elite(
    simbolo: str,
    direccion: str,
    precio_entrada: float,
    atr: float,
    confianza: float,
    balance: float,
    riesgo_max_pct: float = 0.01,
    df: Optional[pd.DataFrame] = None,
    rr_mult: float = 1.0,
):
    """
    Wrapper compatible: devuelve (tp, sl, motivo).
    """
    try:
        plan = calcular_plan_tpsl_profesional(
            simbolo=simbolo,
            direccion=direccion,
            precio_entrada=precio_entrada,
            atr=atr,
            confianza=confianza,
            df=df,
            habilitar_tp_parciales=False,
            rr_mult=rr_mult,
        )
        if plan.get("motivo") != "OK":
            return None, None, str(plan.get("motivo"))
        return plan.get("tp"), plan.get("sl"), "OK"
    except Exception as e:
        print(f"⚠️ Error calculando TP/SL Profesional: {e}")
        return None, None, "EXCEPTION"
