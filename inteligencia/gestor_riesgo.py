import configuracion as config
import puente_visual # Para mostrar la "mente" de la IA en pantalla
import json
import math
import os
import time
from datetime import datetime, timedelta

# --- CONFIGURACIÓN CIRCUITO ---
RUTA_PERSISTENCIA = os.path.join(os.path.dirname(__file__), "riesgo_persistencia.json")
RUTA_ESTADO_DIA = os.path.join(os.path.dirname(__file__), "estado_dia.json")
MAX_PERDIDA_DIARIA_PCT = -0.03

RUTA_LOG_NO_ENTRA = os.path.join(os.path.dirname(__file__), "operaciones", "no_entra_motivos.log")
RUTA_TMP_NO_ENTRA = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tmp", "zerox_no_entra.txt"))
RUTA_PARAMETROS_ACTIVOS = os.path.join(os.path.dirname(__file__), "parametros_activos.json")
RUTA_FLAG_RESET_DIA = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tmp", "reset_dia.flag"))
RUTA_FLAG_RESET_RIESGO_HOY = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tmp", "reset_riesgo_hoy.flag"))

def _cargar_parametros_activos():
    """
    Parámetros ajustables (aprendizaje suave). Deben vivir en JSON, nunca auto-editar .py.
    """
    defaults = {
        "timezone": "Europe/Madrid",
        "daily_loss_soft_pct": 3.0,
        "daily_loss_hard_pct": 10.0,
        "cooldown_min": 60,
        "riesgo_base_pct": 1.0,
        "riesgo": {
            "riesgo_min_pct": 0.25,
            "riesgo_max_pct": 2.0,
            "utilizacion_riesgo": 1.0,
            "dd_reduccion_1": 0.9,
            "dd_reduccion_2": 0.75,
            "dd_reduccion_3": 0.5,
        },
        "apalancamiento": {"leverage_max": int(getattr(config, "APALANCAMIENTO_MAX", 5) or 5), "liq_buffer": 0.8},
        "objetivo": {"OBJETIVO_EUR": int(getattr(config, "OBJETIVO_EUR", 10000000) or 10000000), "PERFIL_RIESGO": str(getattr(config, "PERFIL_RIESGO", "AGRESIVO_CONTROLADO") or "AGRESIVO_CONTROLADO")},
        # Compatibilidad: KPI interno también en raíz (no implica promesa de ganancias)
        "OBJETIVO_EUR": int(getattr(config, "OBJETIVO_EUR", 10000000) or 10000000),
    }

    try:
        if os.path.exists(RUTA_PARAMETROS_ACTIVOS):
            with open(RUTA_PARAMETROS_ACTIVOS, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
                if isinstance(data, dict):
                    # Merge shallow + nested conocidos
                    out = dict(defaults)
                    out.update(data)
                    for k in ("riesgo", "apalancamiento", "objetivo"):
                        merged = dict(defaults.get(k, {}))
                        merged.update((data.get(k) or {}) if isinstance(data.get(k), dict) else {})
                        out[k] = merged
                    return out
    except Exception:
        pass

    return defaults


def _clamp_float(x, a, b):
    try:
        x = float(x)
    except Exception:
        x = float(a)
    return float(max(a, min(b, x)))


def obtener_riesgo_pct_operativo(saldo_actual):
    """
    Devuelve riesgo_pct en formato "%", p.ej. 1.0 == 1%.
    Modula suavemente por drawdown diario y por progreso hacia el objetivo (north-star).
    """
    params = _cargar_parametros_activos()

    riesgo_base = _to_float(params.get("riesgo_base_pct", 1.0)) or 1.0
    riesgo_min = _to_float((params.get("riesgo") or {}).get("riesgo_min_pct", 0.25)) or 0.25
    riesgo_max = _to_float((params.get("riesgo") or {}).get("riesgo_max_pct", 2.0)) or 2.0

    # Factor por drawdown diario (antes de bloquear al -3%)
    dd_factor = 1.0
    dd_pct = 0.0
    try:
        saldo_actual = float(saldo_actual)
        estado_dia = _leer_estado_dia(params=params)
        cap_ini = float((estado_dia or {}).get("equity_inicio_dia") or 0.0)
        if cap_ini > 0 and saldo_actual > 0:
            dd_pct = (saldo_actual - cap_ini) / cap_ini
        if dd_pct <= -0.03:
            dd_factor = _to_float((params.get("riesgo") or {}).get("dd_reduccion_3", 0.5)) or 0.5
        elif dd_pct <= -0.02:
            dd_factor = _to_float((params.get("riesgo") or {}).get("dd_reduccion_2", 0.75)) or 0.75
        elif dd_pct <= -0.01:
            dd_factor = _to_float((params.get("riesgo") or {}).get("dd_reduccion_1", 0.9)) or 0.9
    except Exception:
        dd_factor = 1.0
        dd_pct = 0.0

    # Factor por progreso hacia objetivo (suave, no agresivo de golpe)
    obj = _to_float((params.get("objetivo") or {}).get("OBJETIVO_EUR", 10000000)) or 10000000
    progreso = 0.0
    try:
        saldo_actual = float(saldo_actual)
        if obj > 0:
            progreso = saldo_actual / obj
    except Exception:
        progreso = 0.0

    progreso_factor = 1.0
    if progreso < 0.0005:
        progreso_factor = 1.15
    elif progreso < 0.0025:
        progreso_factor = 1.05
    elif progreso > 0.05:
        progreso_factor = 0.85
    elif progreso > 0.2:
        progreso_factor = 0.7

    riesgo = float(riesgo_base) * float(dd_factor) * float(progreso_factor)
    riesgo = _clamp_float(riesgo, riesgo_min, riesgo_max)
    return round(riesgo, 3)


def obtener_rr_mult_operativo(saldo_actual):
    """
    Multiplicador suave de RR (no garantiza nada; solo modula ambición del TP).
    - Base: r_reward_mult (parametros_activos.json)
    - Ajuste por drawdown diario y progreso objetivo.
    """
    params = _cargar_parametros_activos()
    base = _to_float(params.get("r_reward_mult", 1.0)) or 1.0

    dd_factor = 1.0
    dd_pct = 0.0
    try:
        saldo_actual = float(saldo_actual)
        estado_dia = _leer_estado_dia(params=params)
        cap_ini = float((estado_dia or {}).get("equity_inicio_dia") or 0.0)
        if cap_ini > 0 and saldo_actual > 0:
            dd_pct = (saldo_actual - cap_ini) / cap_ini
        if dd_pct <= -0.03:
            dd_factor = 0.9
        elif dd_pct <= -0.02:
            dd_factor = 0.95
        elif dd_pct >= 0.02:
            dd_factor = 1.05
    except Exception:
        dd_factor = 1.0

    obj = _to_float((params.get("objetivo") or {}).get("OBJETIVO_EUR", 10000000)) or 10000000
    progreso = 0.0
    try:
        if obj > 0:
            progreso = float(saldo_actual) / obj
    except Exception:
        progreso = 0.0

    progreso_factor = 1.0
    if progreso < 0.0005:
        progreso_factor = 1.05
    elif progreso > 0.05:
        progreso_factor = 0.95
    elif progreso > 0.2:
        progreso_factor = 0.9

    mult = float(base) * float(dd_factor) * float(progreso_factor)
    return round(_clamp_float(mult, 0.8, 1.25), 3)

def _log_no_entra(payload):
    try:
        os.makedirs(os.path.dirname(RUTA_LOG_NO_ENTRA), exist_ok=True)
        with open(RUTA_LOG_NO_ENTRA, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

        # Último motivo (humano) para pegar/diagnóstico rápido
        try:
            os.makedirs(os.path.dirname(RUTA_TMP_NO_ENTRA), exist_ok=True)
            qty = payload.get("amount")
            if qty is None:
                qty = payload.get("required_amount")

            lineas = [
                f"ts={payload.get('ts')}",
                f"simbolo={payload.get('simbolo')}",
                f"motivo={payload.get('motivo')}",
                f"saldo={payload.get('saldo')}",
                f"min_cost={payload.get('min_cost')}",
                f"L_sugerido={payload.get('leverage_sugerido')}",
                f"L_elegido={payload.get('leverage_elegido', payload.get('leverage'))}",
                f"qty={qty}",
                f"notional={payload.get('notional')}",
                f"margin_req={payload.get('margin_req')}",
                f"max_margin={payload.get('max_margin')}",
                f"riesgo_usdt_obj={payload.get('riesgo_usdt_obj')}",
                f"riesgo_usdt_estimado={payload.get('riesgo_usdt_estimado')}",
            ]
            with open(RUTA_TMP_NO_ENTRA, "w", encoding="utf-8") as f:
                f.write("\n".join(lineas).strip() + "\n")
        except Exception:
            pass
    except Exception:
        pass

def _to_float(value):
    try:
        return float(value)
    except Exception:
        return None

def _normalizar_riesgo_pct(riesgo_pct):
    r = _to_float(riesgo_pct)
    if r is None or r <= 0:
        return None
    # If already a fraction (0.01 == 1%), keep it.
    if r <= 0.2:
        return r
    # If percent (1.0 == 1%), convert to fraction.
    if r <= 100:
        return r / 100.0
    return 1.0

def _clamp_int(value, min_value, max_value):
    try:
        iv = int(value)
    except Exception:
        iv = min_value
    return max(min_value, min(iv, max_value))

def seleccionar_apalancamiento_para_minimo(max_margin_usdt, min_cost_usdt, Lmax, L_sugerido, buffer=0.95):
    """
    Selección determinista de apalancamiento para cumplir el mínimo del exchange SIN aumentar el riesgo por SL.

    Regla:
      - L_necesario = ceil(min_cost_usdt / (max_margin_usdt * buffer))
      - L = clamp(L_necesario, 1, min(Lmax, L_sugerido))
    """
    try:
        max_margin_usdt = float(max_margin_usdt)
        min_cost_usdt = float(min_cost_usdt)
    except Exception:
        return 1

    try:
        buffer = float(buffer)
    except Exception:
        buffer = 0.95

    if max_margin_usdt <= 0 or min_cost_usdt <= 0 or buffer <= 0:
        return 1

    try:
        Lmax = int(Lmax)
    except Exception:
        Lmax = 1
    try:
        L_sugerido = int(L_sugerido)
    except Exception:
        L_sugerido = 1

    upper = max(1, min(Lmax, L_sugerido))
    L_necesario = int(math.ceil(min_cost_usdt / (max_margin_usdt * buffer)))
    L = _clamp_int(L_necesario, 1, upper)

    print(f"AUTO-APALANCAMIENTO: L={L} para cumplir minimo del exchange")
    return int(L)

def _obtener_lmax_respaldo():
    """
    Respaldo conservador si CCXT no expone límites de apalancamiento del mercado.
    """
    for key in ("APALANCAMIENTO_MAX", "MAX_APALANCAMIENTO", "LEVERAGE_MAX"):
        try:
            v = getattr(config, key)
            v = int(v)
            if v > 0:
                return v
        except Exception:
            continue
    try:
        v = int(getattr(config, "APALANCAMIENTO", 1))
        return max(1, v)
    except Exception:
        return 1

def _obtener_limites_apalancamiento_mercado(mercado):
    limites = ((mercado or {}).get("limits") or {})
    limites_lev = (limites.get("leverage") or {})
    min_lev = _to_float(limites_lev.get("min")) or 1.0
    max_lev = _to_float(limites_lev.get("max"))
    return min_lev, max_lev

def _info_mercado(exchange, simbolo):
    try:
        return exchange.market(simbolo) or {}
    except Exception:
        try:
            exchange.load_markets()
            return exchange.market(simbolo) or {}
        except Exception:
            return {}

def _ajustar_cantidad_precision(exchange, simbolo, cantidad, mercado):
    try:
        return float(exchange.amount_to_precision(simbolo, cantidad))
    except Exception:
        try:
            return float(cantidad)
        except Exception:
            return None

def _redondear_cantidad_paso(cantidad, mercado):
    prec = (mercado or {}).get("precision", {}) or {}
    paso = prec.get("amount")
    try:
        paso = float(paso)
    except Exception:
        paso = None

    try:
        cantidad = float(cantidad)
    except Exception:
        return None

    if not paso or paso <= 0:
        return cantidad

    return math.ceil(cantidad / paso) * paso

def _calcular_tamano_posicion_ccxt(exchange, simbolo, precio_entrada, precio_sl, saldo_cuenta, riesgo_pct=1.0, apalancamiento=1, **_):
    ts = datetime.now().isoformat()
    params_activos = _cargar_parametros_activos()

    pe = _to_float(precio_entrada)
    ps = _to_float(precio_sl)
    saldo = _to_float(saldo_cuenta)

    mercado = _info_mercado(exchange, simbolo)
    limits = (mercado.get("limits") or {})

    min_lev_market, max_lev_market = _obtener_limites_apalancamiento_mercado(mercado)
    min_lev = int(max(1, min_lev_market))
    if max_lev_market is not None and max_lev_market > 0:
        Lmax = int(max_lev_market)
    else:
        Lmax = int(_obtener_lmax_respaldo())

    # Cap global por configuración dinámica (parametros_activos.json)
    try:
        cap_cfg = int(((params_activos.get("apalancamiento") or {}).get("leverage_max")))
        if cap_cfg > 0:
            Lmax = int(max(1, min(Lmax, cap_cfg)))
    except Exception:
        pass

    try:
        L_sugerido = int(apalancamiento)
    except Exception:
        L_sugerido = 1
    if L_sugerido <= 0:
        L_sugerido = 1

    min_cost = _to_float((limits.get("cost") or {}).get("min"))
    if min_cost is None or min_cost <= 0:
        min_cost = 5.0

    min_amount = _to_float((limits.get("amount") or {}).get("min")) or 0.0
    contract_size = _to_float(mercado.get("contractSize")) or 1.0
    if contract_size <= 0:
        contract_size = 1.0

    if pe is None or pe <= 0 or ps is None or saldo is None or saldo <= 0:
        _log_no_entra({
            "ts": ts,
            "simbolo": simbolo,
            "motivo": "INPUT_INVALIDO",
            "saldo": saldo_cuenta,
            "entrada": precio_entrada,
            "sl": precio_sl,
            "min_cost": min_cost,
            "min_amount": min_amount,
            "leverage_sugerido": L_sugerido,
        })
        return 0.0, _clamp_int(L_sugerido, 1, max(1, min(Lmax, L_sugerido)))

    stop_dist = abs(pe - ps)
    if stop_dist <= 0:
        _log_no_entra({
            "ts": ts,
            "simbolo": simbolo,
            "motivo": "SL_INVALIDO",
            "saldo": saldo,
            "entrada": pe,
            "sl": ps,
            "min_cost": min_cost,
            "min_amount": min_amount,
            "leverage_sugerido": L_sugerido,
        })
        return 0.0, _clamp_int(L_sugerido, 1, max(1, min(Lmax, L_sugerido)))

    # Límite de apalancamiento por seguridad de liquidación vs SL (aprox):
    # Queremos que la liquidación quede MÁS lejos que el SL.
    try:
        liq_buffer = float((params_activos.get("apalancamiento") or {}).get("liq_buffer", 0.8))
    except Exception:
        liq_buffer = 0.8
    if liq_buffer <= 0 or liq_buffer > 0.95:
        liq_buffer = 0.8

    stop_dist_frac = (stop_dist / pe) if pe > 0 else 0.0
    if stop_dist_frac > 0:
        L_max_liq = int(max(1, math.floor(liq_buffer / stop_dist_frac)))
    else:
        L_max_liq = 1

    L_upper = int(max(min_lev, min(Lmax, L_max_liq)))
    leverage_final = _clamp_int(L_sugerido, min_lev, L_upper)

    # Clamp del riesgo configurable (evita locuras si llega un valor fuera de rango)
    try:
        rmin = float((params_activos.get("riesgo") or {}).get("riesgo_min_pct", 0.25))
        rmax = float((params_activos.get("riesgo") or {}).get("riesgo_max_pct", 2.0))
        rv = _to_float(riesgo_pct)
        if rv is not None and rv > 0:
            if rv <= 0.2:
                rv = _clamp_float(rv, rmin / 100.0, rmax / 100.0)
            else:
                rv = _clamp_float(rv, rmin, rmax)
            riesgo_pct = rv
    except Exception:
        pass

    riesgo_frac = _normalizar_riesgo_pct(riesgo_pct)
    if riesgo_frac is None:
        _log_no_entra({"ts": ts, "simbolo": simbolo, "motivo": "RIESGO_INVALIDO", "riesgo_pct": riesgo_pct, "leverage_sugerido": L_sugerido})
        return 0.0, _clamp_int(L_sugerido, 1, max(1, min(Lmax, L_sugerido)))

    risk_usdt_target = saldo * riesgo_frac
    if risk_usdt_target <= 0:
        _log_no_entra({"ts": ts, "simbolo": simbolo, "motivo": "RIESGO_CERO", "saldo": saldo, "riesgo_frac": riesgo_frac, "leverage_sugerido": L_sugerido})
        return 0.0, _clamp_int(L_sugerido, 1, max(1, min(Lmax, L_sugerido)))

    max_margin = saldo * 0.95

    # Si el minimo de notional es imposible incluso con Lmax, no entra (y luego el filtro de mercados lo excluirá).
    max_notional_teorico = max_margin * float(Lmax) * 0.95
    if min_cost > max_notional_teorico:
        _log_no_entra({
            "ts": ts,
            "simbolo": simbolo,
            "motivo": "MIN_COST_IMPOSIBLE_POR_MARGEN",
            "saldo": saldo,
            "entrada": pe,
            "sl": ps,
            "min_cost": min_cost,
            "max_margin": max_margin,
            "Lmax": Lmax,
            "leverage_sugerido": L_sugerido,
        })
        return 0.0, 1

    required_amount = max(min_amount, min_cost / (pe * contract_size))
    amount_max_riesgo = risk_usdt_target / (contract_size * stop_dist)

    # Tamaño mínimo para cumplir exchange, pero sin romper el riesgo por SL.
    if required_amount > amount_max_riesgo:
        # --- LÓGICA AGRESIVA PARA CUENTAS PEQUEÑAS (SOLICITUD DE USUARIO: "VÍA LIBRE SI SALDO > 5 USD") ---
        # Si la cuenta es pequeña (< 250 USD) y tiene al menos 5 USD, permitimos entrar con el mínimo del exchange
        # aunque viole todas las normas de riesgo porcentual.
        # "SOLAMENTE DEBE BLOQUEARSE CUANDO HAYA MENOS DE 5 USD EN LA CUENTA, EL RESTO VÍA LIBRE"
        
        es_cuenta_pequena = (saldo < 250.0)
        es_cuenta_viable = (saldo >= 5.0) # Buffer mínimo de supervivencia
        
        riesgo_usdt_minimo_ex = required_amount * contract_size * stop_dist
        riesgo_pct_minimo_ex = (riesgo_usdt_minimo_ex / saldo) if saldo > 0 else 1.0
        
        if es_cuenta_pequena and es_cuenta_viable:
            print(f"⚠️ MODO AGRESIVO ACTIVADO: Cuenta pequeña ({saldo:.2f}$). Ignorando limites de riesgo para cumplir minimo exchange.")
            print(f"   -> Riesgo teórico: {riesgo_pct_minimo_ex*100:.2f}% | Requerido {required_amount} uds.")
            
            # Aceptamos el required_amount como el nuevo amount target EXCEPTO si nos liquida instantáneamente (>90% equity).
            if riesgo_pct_minimo_ex < 0.90:
                amount_max_riesgo = required_amount
                # Elevamos el target de riesgo para que validaciones posteriores no bloqueen
                risk_usdt_target = max(risk_usdt_target, riesgo_usdt_minimo_ex * 1.5)
            else:
                 # Si el SL nos quita el 90% de la cuenta, eso ya es suicidio matemático, bloqueamos igual.
                 _log_no_entra({
                    "ts": ts,
                    "simbolo": simbolo,
                    "motivo": "RIESGO_SUICIDA_90PCT",
                    "saldo": saldo,
                    "riesgo_pct_real": f"{riesgo_pct_minimo_ex*100:.2f}%"
                })
                 return 0.0, leverage_final
        else:
            # Si supera incluso el tope de seguridad o no hay saldo minimo
            riesgo_usdt_min = required_amount * contract_size * stop_dist
            _log_no_entra({
                "ts": ts,
                "simbolo": simbolo,
                "motivo": "MINIMO_SUPERA_RIESGO",
                "saldo": saldo,
                "entrada": pe,
                "sl": ps,
                "stop_dist": stop_dist,
                "riesgo_frac_obj": riesgo_frac,
                "riesgo_usdt_obj": risk_usdt_target,
                "riesgo_usdt_estimado": riesgo_usdt_min,
                "riesgo_pct_real": f"{riesgo_pct_minimo_ex*100:.2f}%",
                "min_cost": min_cost,
                "min_amount": min_amount,
                "required_amount": required_amount,
                "leverage_sugerido": L_sugerido,
                "leverage_elegido": leverage_final,
            })
            return 0.0, leverage_final

    # Tamaño objetivo: usar el presupuesto de riesgo (no quedarnos en el mínimo del exchange).
    try:
        util_riesgo = float((params_activos.get("riesgo") or {}).get("utilizacion_riesgo", 1.0))
    except Exception:
        util_riesgo = 1.0
    util_riesgo = float(max(0.2, min(1.0, util_riesgo)))

    amount_obj = amount_max_riesgo * util_riesgo
    amount = max(required_amount, amount_obj)

    amount_prec = _ajustar_cantidad_precision(exchange, simbolo, amount, mercado)
    if amount_prec is None or amount_prec <= 0:
        _log_no_entra({"ts": ts, "simbolo": simbolo, "motivo": "PRECISION_INVALIDA", "amount": amount, "leverage_sugerido": L_sugerido, "leverage_elegido": leverage_final})
        return 0.0, leverage_final

    if amount_prec < required_amount:
        amount_up = _redondear_cantidad_paso(required_amount, mercado)
        amount_up = _ajustar_cantidad_precision(exchange, simbolo, amount_up, mercado)
        if amount_up is None or amount_up < required_amount:
            _log_no_entra({
                "ts": ts,
                "simbolo": simbolo,
                "motivo": "NO_CUMPLE_MINIMOS_PRECISION",
                "amount_prec": amount_prec,
                "required_amount": required_amount,
                "min_cost": min_cost,
                "min_amount": min_amount,
                "leverage_sugerido": L_sugerido,
                "leverage_elegido": leverage_final,
            })
            return 0.0, leverage_final
        amount_prec = amount_up

    riesgo_usdt_estimado = amount_prec * contract_size * stop_dist
    if riesgo_usdt_estimado > (risk_usdt_target * 1.0001):
        _log_no_entra({
            "ts": ts,
            "simbolo": simbolo,
            "motivo": "PRECISION_SUPERA_RIESGO",
            "saldo": saldo,
            "entrada": pe,
            "sl": ps,
            "stop_dist": stop_dist,
            "amount": amount_prec,
            "min_cost": min_cost,
            "min_amount": min_amount,
            "riesgo_frac_obj": riesgo_frac,
            "riesgo_usdt_obj": risk_usdt_target,
            "riesgo_usdt_estimado": riesgo_usdt_estimado,
            "leverage_sugerido": L_sugerido,
            "leverage_elegido": leverage_final,
        })
        return 0.0, leverage_final

    notional = amount_prec * contract_size * pe

    # Recalcular apalancamiento si el notional final (tras precisión) requiere más margen del previsto.
    leverage_necesario_notional = int(math.ceil(notional / (max_margin * 0.95))) if max_margin > 0 else 1
    if leverage_necesario_notional > leverage_final:
        upper = int(max(1, L_upper))
        leverage_ajustado = _clamp_int(leverage_necesario_notional, min_lev, upper)
        if leverage_ajustado != leverage_final:
            print(f"AUTO-APALANCAMIENTO: reajuste L={leverage_ajustado} por margen tras precision")
            leverage_final = leverage_ajustado

    # Si ni con el máximo permitido (por SL/liquidación) cabe el margen, reducimos tamaño (sin romper mínimos).
    if leverage_necesario_notional > int(max(1, L_upper)):
        try:
            max_notional_fit = max_margin * float(int(max(1, L_upper))) * 0.95
            amount_fit = max_notional_fit / (contract_size * pe) if (contract_size * pe) > 0 else 0.0
        except Exception:
            amount_fit = 0.0

        if amount_fit <= 0 or amount_fit < required_amount:
            _log_no_entra({
                "ts": ts,
                "simbolo": simbolo,
                "motivo": "MARGIN_INSUFICIENTE_POR_LIMITE_LIQ",
                "saldo": saldo,
                "entrada": pe,
                "sl": ps,
                "required_amount": required_amount,
                "amount_fit": amount_fit,
                "min_cost": min_cost,
                "max_margin": max_margin,
                "Lmax": Lmax,
                "L_upper": int(max(1, L_upper)),
                "leverage_sugerido": L_sugerido,
                "leverage_elegido": leverage_final,
            })
            return 0.0, leverage_final

        amount_fit_prec = _ajustar_cantidad_precision(exchange, simbolo, amount_fit, mercado)
        if amount_fit_prec is None or amount_fit_prec < required_amount:
            amount_up = _redondear_cantidad_paso(required_amount, mercado)
            amount_fit_prec = _ajustar_cantidad_precision(exchange, simbolo, amount_up, mercado)

        if amount_fit_prec is None or amount_fit_prec < required_amount:
            _log_no_entra({
                "ts": ts,
                "simbolo": simbolo,
                "motivo": "NO_CUMPLE_MINIMOS_POR_MARGEN_LIQ",
                "saldo": saldo,
                "entrada": pe,
                "sl": ps,
                "required_amount": required_amount,
                "amount_fit_prec": amount_fit_prec,
                "min_cost": min_cost,
                "max_margin": max_margin,
                "L_upper": int(max(1, L_upper)),
                "leverage_sugerido": L_sugerido,
                "leverage_elegido": leverage_final,
            })
            return 0.0, leverage_final

        if float(amount_fit_prec) < float(amount_prec):
            print(f"AUTO-SIZING: reduciendo cantidad por margen+limite_liq (qty {amount_prec} -> {amount_fit_prec})")
        amount_prec = float(min(float(amount_prec), float(amount_fit_prec)))
        notional = amount_prec * contract_size * pe
        riesgo_usdt_estimado = amount_prec * contract_size * stop_dist

    margin_req = notional / max(leverage_final, 1)

    if notional < min_cost:
        _log_no_entra({
            "ts": ts,
            "simbolo": simbolo,
            "motivo": "MIN_COST",
            "saldo": saldo,
            "entrada": pe,
            "sl": ps,
            "amount": amount_prec,
            "notional": notional,
            "min_cost": min_cost,
            "min_amount": min_amount,
            "leverage_sugerido": L_sugerido,
            "leverage_elegido": leverage_final,
        })
        return 0.0, leverage_final

    if margin_req > max_margin:
        _log_no_entra({
            "ts": ts,
            "simbolo": simbolo,
            "motivo": "MARGIN_INSUFICIENTE",
            "saldo": saldo,
            "entrada": pe,
            "sl": ps,
            "amount": amount_prec,
            "notional": notional,
            "margin_req": margin_req,
            "max_margin": max_margin,
            "min_cost": min_cost,
            "min_amount": min_amount,
            "leverage_sugerido": L_sugerido,
            "leverage_elegido": leverage_final,
        })
        return 0.0, leverage_final

    return float(amount_prec), int(leverage_final)

def calcular_tamano_posicion(*args, **kwargs):
    """
    Wrapper tolerante (no falla por kwargs inesperados):
    - calcular_tamano_posicion(confianza_ia, saldo_cuenta) -> float
    - calcular_tamano_posicion(exchange, simbolo, precio_entrada, precio_sl, saldo_cuenta, riesgo_pct=..., apalancamiento=...) -> (amount, leverage)
    """
    try:
        if args and hasattr(args[0], "fetch_balance") and len(args) >= 5:
            exchange, simbolo, precio_entrada, precio_sl, saldo_cuenta = args[:5]
            riesgo_pct = kwargs.get("riesgo_pct", kwargs.get("porcentaje_riesgo", kwargs.get("risk_pct", 1.0)))
            apalancamiento = kwargs.get("apalancamiento", kwargs.get("leverage", 1))
            return _calcular_tamano_posicion_ccxt(
                exchange, simbolo, precio_entrada, precio_sl, saldo_cuenta,
                riesgo_pct=riesgo_pct, apalancamiento=apalancamiento
            )

        if len(args) >= 2:
            return _calcular_tamano_posicion_por_confianza(args[0], args[1])
        if "confianza_ia" in kwargs and "saldo_cuenta" in kwargs:
            return _calcular_tamano_posicion_por_confianza(kwargs["confianza_ia"], kwargs["saldo_cuenta"])

        return 0.0
    except Exception as e:
        _log_no_entra({"ts": datetime.now().isoformat(), "motivo": "EXCEPTION", "error": str(e), "args_len": len(args)})
        if args and hasattr(args[0], "fetch_balance"):
            return 0.0, 1
        return 0.0


def calcular_tamano_posicion_offline(
    simbolo: str,
    precio_entrada: float,
    precio_sl: float,
    saldo_cuenta: float,
    riesgo_pct: float = 1.0,
    apalancamiento: int = 1,
    min_cost_usdt: float = 5.0,
):
    """
    Sizing determinista SIN exchange (fallback para MODO_MANTENIMIENTO / sin red):
    - qty ≈ riesgo_usdt / distancia_sl
    - valida mÍnimo notional (min_cost_usdt) sin romper el riesgo (si lo rompe => NO_ENTRA)

    Devuelve (cantidad, leverage_final).
    """
    ts = datetime.now().isoformat()

    pe = _to_float(precio_entrada)
    ps = _to_float(precio_sl)
    saldo = _to_float(saldo_cuenta)

    try:
        L_sugerido = int(apalancamiento)
    except Exception:
        L_sugerido = 1
    if L_sugerido <= 0:
        L_sugerido = 1

    # Cap por parametros_activos.json (si existe)
    Lmax = None
    try:
        params_activos = _cargar_parametros_activos()
        cap_cfg = int(((params_activos.get("apalancamiento") or {}).get("leverage_max")))
        if cap_cfg > 0:
            Lmax = cap_cfg
    except Exception:
        Lmax = None

    if Lmax is None:
        Lmax = _obtener_lmax_respaldo()

    leverage_final = _clamp_int(L_sugerido, 1, max(1, int(Lmax)))

    if pe is None or pe <= 0 or ps is None or saldo is None or saldo <= 0:
        _log_no_entra({"ts": ts, "simbolo": simbolo, "motivo": "INPUT_INVALIDO_OFFLINE", "saldo": saldo_cuenta, "entrada": precio_entrada, "sl": precio_sl})
        return 0.0, leverage_final

    stop_dist = abs(pe - ps)
    if stop_dist <= 0:
        _log_no_entra({"ts": ts, "simbolo": simbolo, "motivo": "SL_INVALIDO_OFFLINE", "saldo": saldo, "entrada": pe, "sl": ps})
        return 0.0, leverage_final

    riesgo_frac = _normalizar_riesgo_pct(riesgo_pct)
    if riesgo_frac is None:
        _log_no_entra({"ts": ts, "simbolo": simbolo, "motivo": "RIESGO_INVALIDO_OFFLINE", "riesgo_pct": riesgo_pct})
        return 0.0, leverage_final

    risk_usdt_target = saldo * riesgo_frac
    if risk_usdt_target <= 0:
        _log_no_entra({"ts": ts, "simbolo": simbolo, "motivo": "RIESGO_CERO_OFFLINE", "saldo": saldo, "riesgo_frac": riesgo_frac})
        return 0.0, leverage_final

    try:
        min_cost = float(min_cost_usdt or 0.0)
    except Exception:
        min_cost = 5.0
    if min_cost <= 0:
        min_cost = 5.0

    required_amount = (min_cost / pe) if pe > 0 else 0.0
    amount_max_riesgo = risk_usdt_target / stop_dist

    if required_amount > amount_max_riesgo:
        _log_no_entra({
            "ts": ts,
            "simbolo": simbolo,
            "motivo": "MINIMO_SUPERA_RIESGO_OFFLINE",
            "saldo": saldo,
            "entrada": pe,
            "sl": ps,
            "stop_dist": stop_dist,
            "riesgo_usdt_obj": risk_usdt_target,
            "min_cost": min_cost,
            "required_amount": required_amount,
            "amount_max_riesgo": amount_max_riesgo,
            "leverage_sugerido": L_sugerido,
            "leverage_elegido": leverage_final,
        })
        return 0.0, leverage_final

    amount = max(required_amount, amount_max_riesgo)
    try:
        amount = round(float(amount), 6)
    except Exception:
        amount = 0.0

    if amount <= 0:
        _log_no_entra({"ts": ts, "simbolo": simbolo, "motivo": "AMOUNT_CERO_OFFLINE", "amount": amount})
        return 0.0, leverage_final

    return float(amount), int(leverage_final)

def _calcular_tamano_posicion_por_confianza(confianza_ia, saldo_cuenta):
    """
    Calcula tamaño posición CON REGLAS DE ORO (Máx 1% Riesgo).
    """
    # 1. Normalizar confianza a %
    if confianza_ia <= 1.0: 
        confianza_pct = confianza_ia * 100
    else:
        confianza_pct = confianza_ia

    # 2. GATING POR CONFIANZA IA
    if confianza_pct < 60:
        puente_visual.actualizar_estado({
            "confianza_ia": f"{confianza_pct:.1f}%",
            "nivel_riesgo": "BLOQUEADO (<60%)",
            "capital_arriesgado": "0.00 USDT"
        })
        return 0.0

    # 3. ESCALADO DE RIESGO (Conservador)
    # Solo dos niveles: Medio (0.5%) o "Full" (1%)
    porcentaje_riesgo = 0.005 # 0.5% por defecto w
    etiqueta_riesgo = "MEDIO (0.5%)"

    if confianza_pct > 80:
        porcentaje_riesgo = 0.01 # 1% Máximo Absoluto
        etiqueta_riesgo = "NORMAL (1%)"

    cantidad_usdt = saldo_cuenta * porcentaje_riesgo
    
    # 4. LÍMITE DE EXCHANGE (Bitget mín ~5 USDT)
    # Si el 1% es menor al mínimo, NO OPERAMOS (Preservación de capital)
    # Regla: No forzar trades si la cuenta es pequeña.
    MINIMO_EXCHANGE = 5.0
    if cantidad_usdt < MINIMO_EXCHANGE:
        # Excepción única: Si tenemos saldo y queremos probar, usamos el mínimo EXACTO
        # pero SOLO si eso no representa más del 5% del saldo total (para cuentas micro)
        if saldo_cuenta * 0.05 >= MINIMO_EXCHANGE:
            cantidad_usdt = MINIMO_EXCHANGE
            etiqueta_riesgo = "MÍNIMO (Micro)"
        else:
            cantidad_usdt = 0.0
            etiqueta_riesgo = "CAPITAL INSUFICIENTE (Riesgo > 5%)"

    # --- PUNTUACIÓN VISUAL ---
    puente_visual.actualizar_estado({
        "confianza_ia": f"{confianza_pct:.1f}%",
        "nivel_riesgo": etiqueta_riesgo,
        "capital_arriesgado": f"{cantidad_usdt:.2f} USDT"
    })

    return round(cantidad_usdt, 2)

def registrar_tpsl_preview(simbolo, metodo, entrada, tp, sl, atr, mult_sl, r_ratio, confianza):
    """Loguea la decisión de TP/SL para auditoría visual."""
    ruta = os.path.join(os.path.dirname(__file__), "operaciones", "preview_tpsl.log")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    
    dist_sl_pct = abs(entrada - sl) / entrada * 100
    dist_tp_pct = abs(tp - entrada) / entrada * 100
    
    linea = (
        f"[{datetime.now().strftime('%H:%M:%S')}] {simbolo} | Metodo: {metodo} | "
        f"Confianza: {confianza}% | ATR: {atr:.4f} | "
        f"In: {entrada} -> SL: {sl} ({dist_sl_pct:.2f}%) | TP: {tp} ({dist_tp_pct:.2f}%) | "
        f"MultSL: {mult_sl} | R: {r_ratio}\n"
    )
    
    try:
        with open(ruta, "a", encoding="utf-8") as f: f.write(linea)
    except: pass

def calcular_tpsl_elite(simbolo, lado, precio_entrada, atr=None, confianza=60.0):
    """
    Calcula TP/SL Determinista y Auditado (Nada de magia).
    
    REGLAS DE ORO:
    1. Base ATR (Volatilidad) si existe.
    2. Multiplicadores ajustados por confianza (Clamp).
    3. Límites duros (Hard Limits): Máx SL 2.5%, Mín 0.3%.
    """
    lado = lado.upper() # LONG / SHORT
    
    # 1. DEFINIR MULTIPLICADORES BASE (CLAMP)
    # Entre 60 y 75: Conservador
    # Entre 76 y 85: Normal
    # > 85: Agresivo (Deja correr más TP, aprieta SL)
    
    if confianza > 85:
        mult_atr_sl = 1.0   # SL ajustado
        ratio_tp = 2.0      # Buscar 1:2
    elif confianza > 75:
        mult_atr_sl = 1.2   # Standard
        ratio_tp = 1.5      # Buscar 1:1.5
    else:
        mult_atr_sl = 1.5   # SL más holgado (incertidumbre)
        ratio_tp = 1.3      # TP corto (asegurar)
        
    metodo = "ATR_ELITE"
    
    # 2. CALCULO BASE
    sl_dist = 0.0
    
    if atr and atr > 0:
        sl_dist = atr * mult_atr_sl
    else:
        # FALLBACK: 1.5% SL Fijo
        metodo = "FALLBACK_FIXED"
        sl_dist = precio_entrada * 0.015
        atr = 0.0

    # 3. LÍMITES DUROS (HARD LIMITS)
    dist_pct = (sl_dist / precio_entrada) * 100
    
    # Mínimo absoluto: 0.3% (evitar ser barrido por ruido)
    if dist_pct < 0.3:
        sl_dist = precio_entrada * 0.003
        metodo += "_CLAMP_MIN"
        
    # Máximo absoluto: 2.5% (Evitar catástrofe)
    if dist_pct > 2.5:
        sl_dist = precio_entrada * 0.025
        metodo += "_CLAMP_MAX"
        
    # 4. PROYECCIÓN DE PRECIOS
    if lado == "LONG":
        sl = precio_entrada - sl_dist
        tp_dist = sl_dist * ratio_tp
        tp = precio_entrada + tp_dist
    else: # SHORT
        sl = precio_entrada + sl_dist
        tp_dist = sl_dist * ratio_tp
        tp = precio_entrada - tp_dist
        
    # 5. REDONDEO (4 decimales estándar USDT)
    sl = round(sl, 4)
    tp = round(tp, 4)
    
    # 6. LOG DE AUDITORÍA
    registrar_tpsl_preview(simbolo, metodo, precio_entrada, tp, sl, atr, mult_atr_sl, ratio_tp, confianza)
    
    return tp, sl

# Wrapper para compatibilidad con código viejo
def calcular_niveles_salida(precio_entrada, tipo_orden):
    return calcular_tpsl_elite("UNKNOWN", tipo_orden, precio_entrada, atr=None, confianza=70)

# ==========================================
# 🛡️ CIRCUIT BREAKERS & PERSISTENCIA
# ==========================================

def _tzinfo_desde_params(params):
    tz_name = str((params or {}).get("timezone") or "Europe/Madrid")
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(tz_name)
    except Exception:
        return None


def _fecha_local_hoy(params):
    tz = _tzinfo_desde_params(params)
    try:
        now = datetime.now(tz) if tz else datetime.now()
    except Exception:
        now = datetime.now()
    return now.strftime("%Y-%m-%d")


def _inicio_siguiente_dia_ts(params):
    tz = _tzinfo_desde_params(params)
    ahora = datetime.now(tz) if tz else datetime.now()
    if tz:
        inicio_hoy = datetime(ahora.year, ahora.month, ahora.day, tzinfo=tz)
    else:
        inicio_hoy = datetime(ahora.year, ahora.month, ahora.day)
    inicio_manana = inicio_hoy + timedelta(days=1)
    try:
        return float(inicio_manana.timestamp())
    except Exception:
        return float(time.time() + 86400)


def _leer_estado_dia(params=None):
    """
    Lee inteligencia/estado_dia.json sin reescribirlo.

    Nota: el reset por cambio de día se hace en `actualizar_estado_dia()` (que se llama desde
    `inicializar_dia()` y desde `verificar_circuit_breaker()` con EQUITY real).
    """
    if params is None:
        params = _cargar_parametros_activos()

    hoy = _fecha_local_hoy(params)
    try:
        if os.path.exists(RUTA_ESTADO_DIA):
            with open(RUTA_ESTADO_DIA, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
                if isinstance(data, dict) and data.get("fecha_local") == hoy:
                    return data
    except Exception:
        return {"fecha_local": hoy, "equity_inicio_dia": 0.0, "equity_max_dia": 0.0}

    return {"fecha_local": hoy, "equity_inicio_dia": 0.0, "equity_max_dia": 0.0}


def _leer_estado_dia_raw(params=None):
    """
    Retorna el contenido del archivo estado_dia.json incluso si la fecha no coincide.
    """
    if params is None:
        params = _cargar_parametros_activos()
    hoy = _fecha_local_hoy(params)
    try:
        if os.path.exists(RUTA_ESTADO_DIA):
            with open(RUTA_ESTADO_DIA, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {"fecha_local": hoy, "equity_inicio_dia": 0.0, "equity_max_dia": 0.0}


def actualizar_estado_dia(equity_actual, params=None):
    """
    Persistencia del baseline diario (Europe/Madrid por defecto):
      inteligencia/estado_dia.json =>
        { "fecha_local": "YYYY-MM-DD", "equity_inicio_dia": X, "equity_max_dia": Y }

    Regla: si cambia el día local, reset automático.
    """
    if params is None:
        params = _cargar_parametros_activos()

    try:
        equity_actual = float(equity_actual or 0.0)
    except Exception:
        equity_actual = 0.0

    hoy = _fecha_local_hoy(params)
    data = {}
    try:
        if os.path.exists(RUTA_ESTADO_DIA):
            with open(RUTA_ESTADO_DIA, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
                if not isinstance(data, dict):
                    data = {}
    except Exception:
        data = {}

    cambiado = False
    
    # Check de Override manual por variable de entorno (una sola vez)
    fuerza_reset = False
    if os.environ.get("RESET_RIESGO_DIARIO") == "1":
        fuerza_reset = True
        os.environ["RESET_RIESGO_DIARIO"] = "0"

    # Check de Override por ARCHIVO (reset_dia.flag)
    # Esto permite al usuario forzar reset creando el archivo sin reiniciar env vars
    if os.path.exists(RUTA_FLAG_RESET_DIA):
        fuerza_reset = True
        try:
            print("⚠️ RESET TOTAL (BACKEND) DETECTADO: Borrando memoria de riesgo y estado diario...")
            # 1. Borrar archivos de estado para un reinicio limpio al 100%
            if os.path.exists(RUTA_ESTADO_DIA):
                os.remove(RUTA_ESTADO_DIA)
                print(f"   - Borrado: {os.path.basename(RUTA_ESTADO_DIA)}")
            
            if os.path.exists(RUTA_PERSISTENCIA):
                os.remove(RUTA_PERSISTENCIA)
                print(f"   - Borrado: {os.path.basename(RUTA_PERSISTENCIA)}")

            # 2. Consumir flag
            os.remove(RUTA_FLAG_RESET_DIA)
            
            # 3. Forzar regeneración de estado en memoria local para esta ejecución
            data = {} 
            # Al estar vacía 'data', el bloque 'if fuerza_reset...' de abajo la rellenará con equity actual
        except Exception as e:
            print(f"❌ Error en Reset Total: {e}")

    if fuerza_reset or data.get("fecha_local") != hoy:
        # RESET DIARIO AUTOMÁTICO (O POST-BORRADO)
        # Si venimos de un borrado, 'data' está vacía o es vieja, así que regeneramos con valores actuales.
        print(f"🔄 NUEVO CICLO (o Reset): {hoy}. Inicializando métricas al 100% con saldo actual.")
        data = {
            "fecha_local": hoy, 
            "equity_inicio_dia": float(equity_actual), 
            "equity_max_dia": float(equity_actual)
        }
        cambiado = True
        
        # En caso de reset automático por fecha (no forzado), limpiar flags de persistencia
        # si es que el archivo existe (si fue reset forzado ya se borró arriba)
        try:
            if os.path.exists(RUTA_PERSISTENCIA):
                p_data = _cargar_persistencia()
                if p_data.get("hard_pausa_dia", False):
                    p_data["hard_pausa_dia"] = False
                    p_data["motivo_pausa"] = None
                    p_data["cooldown_hasta_ts"] = 0
                    _guardar_persistencia(p_data)
        except Exception: pass
    else:
        ini = _to_float(data.get("equity_inicio_dia"))
        mx = _to_float(data.get("equity_max_dia"))

        if ini is None or ini <= 0:
            data["equity_inicio_dia"] = float(equity_actual)
            cambiado = True
        if mx is None or mx <= 0:
            data["equity_max_dia"] = float(equity_actual)
            cambiado = True
        else:
            try:
                if float(equity_actual) > float(mx):
                    data["equity_max_dia"] = float(equity_actual)
                    cambiado = True
            except Exception:
                data["equity_max_dia"] = float(equity_actual)
                cambiado = True

    if cambiado:
        try:
            with open(RUTA_ESTADO_DIA, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    return data


def _reset_diario(params):
    hoy = _fecha_local_hoy(params)
    return {
        "fecha_local": hoy,
        "cooldown_hasta_ts": 0.0,
        "hard_pausa_dia": False,
        "motivo_pausa": None,
        "racha_perdidas": 0,
        "bloqueo_manual": None,
    }


def _chequear_flag_reset_dia():
    try:
        if os.path.exists(RUTA_FLAG_RESET_DIA):
            os.remove(RUTA_FLAG_RESET_DIA)
            return True
    except Exception:
        pass
    return False


def _aplicar_reset_riesgo_hoy():
    if not os.path.exists(RUTA_FLAG_RESET_RIESGO_HOY):
        return False
    try:
        os.remove(RUTA_FLAG_RESET_RIESGO_HOY)
        print("⚠️ RESET_RIESGO_HOY detectado: limpiando baseline diario y persistencia.")
        if os.path.exists(RUTA_ESTADO_DIA):
            os.remove(RUTA_ESTADO_DIA)
        if os.path.exists(RUTA_PERSISTENCIA):
            os.remove(RUTA_PERSISTENCIA)
        return True
    except Exception as e:
        print(f"⚠️ Error aplicando RESET_RIESGO_HOY: {e}")
        return False


def _baseline_valida_previa(estado_previo, hoy):
    if not isinstance(estado_previo, dict):
        return False
    if str(estado_previo.get("fecha_local") or "") != hoy:
        return False
    ini = _to_float(estado_previo.get("equity_inicio_dia"))
    mx = _to_float(estado_previo.get("equity_max_dia"))
    if ini is None or mx is None:
        return False
    return ini > 0 and mx > 0


def _baseline_corrupta(estado_previo, equity_actual, hoy):
    if not isinstance(estado_previo, dict):
        return False, None
    try:
        equity_inicio = float(estado_previo.get("equity_inicio_dia") or 0.0)
        if equity_inicio <= 0 or equity_actual <= 0:
            return False, None
    except Exception:
        return False, None
    if equity_inicio <= equity_actual * 1.5:
        return False, None
    if str(estado_previo.get("baseline_recalibrado_fecha") or "") == hoy:
        return False, equity_inicio
    return True, equity_inicio


def _recalibrar_baseline(equity_actual, params, motivo):
    data = actualizar_estado_dia(equity_actual, params=params)
    hoy = _fecha_local_hoy(params)
    data["baseline_recalibrado_fecha"] = hoy
    data["baseline_recalibrado_motivo"] = motivo
    try:
        with open(RUTA_ESTADO_DIA, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
    print(f"⚠️ RIESGO DIARIO: {motivo}")
    return data


def _cargar_persistencia(params=None):
    """Carga estado de riesgo (cooldowns/pausas) del disco con reset diario (fecha local)."""
    if params is None:
        params = _cargar_parametros_activos()

    try:
        if os.path.exists(RUTA_PERSISTENCIA):
            with open(RUTA_PERSISTENCIA, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
                if not isinstance(data, dict):
                    data = {}

                # Migración suave de claves antiguas
                if "fecha_local" not in data and "fecha" in data:
                    data["fecha_local"] = data.get("fecha")

                # Eliminar bloqueos legacy (antes era permanente por -3%): ahora se calcula por equity + cooldown.
                data.pop("estado_bloqueo", None)
                data.pop("capital_inicial_dia", None)
                data.pop("fecha", None)

                hoy = _fecha_local_hoy(params)
                if data.get("fecha_local") != hoy:
                    return _reset_diario(params)

                base = _reset_diario(params)
                base.update(data)
                return base
    except Exception as e:
        print(f"⚠️ Error cargando persistencia riesgo: {e}")

    return _reset_diario(params)


def _guardar_persistencia(data):
    try:
        with open(RUTA_PERSISTENCIA, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def inicializar_dia(saldo_actual):
    """Fija el baseline de equity del día al arrancar (inteligencia/estado_dia.json)."""
    params = _cargar_parametros_activos()
    actualizar_estado_dia(saldo_actual, params=params)
    # Alinear persistencia de pausas con el día local (reset si cambió)
    data = _cargar_persistencia(params=params)
    _guardar_persistencia(data)

def verificar_circuit_breaker(saldo_actual, fuente_equity="TOTAL"):
    """
    Verifica si debemos PAUSAR ENTRADAS por riesgo diario (sin apagar el core).

    Importante:
    - Usa EQUITY (balance total), no solo disponible.
    - Persiste baseline diario en inteligencia/estado_dia.json.
    - Nunca hace sys.exit(1): solo devuelve estado.

    Retorna: (permite_entradas: bool, motivo: str, estado_trading: str)
    """
    params = _cargar_parametros_activos()
    hoy = _fecha_local_hoy(params)
    flag_reset = _chequear_flag_reset_dia()
    flag_reset = flag_reset or _aplicar_reset_riesgo_hoy()
    data = _cargar_persistencia(params=params)
    estado_previo = _leer_estado_dia_raw(params=params)
    baseline_previo_valido = _baseline_valida_previa(estado_previo, hoy)
    if flag_reset:
        baseline_previo_valido = False

    # Bloqueo manual (si existiera)
    if data.get("bloqueo_manual"):
        return False, str(data.get("bloqueo_manual")), "BLOQUEADO"

    try:
        equity_actual = float(saldo_actual)
    except Exception:
        equity_actual = 0.0

    # Si no podemos obtener EQUITY válida, tratamos como fallo externo (estado BLOQUEADO, core vivo).
    if equity_actual <= 0:
        return False, "BLOQUEADO: no se pudo obtener EQUITY (balance total) válida.", "BLOQUEADO"

    estado_dia = None
    if not flag_reset:
        corrupto, equity_inicio = _baseline_corrupta(estado_previo, equity_actual, hoy)
        if corrupto:
            motivo_corrupto = (
                "BASELINE CORRUPTO detectado: equity_inicio_dia demasiado superior "
                f"({equity_inicio:.2f}) respecto a equity_actual ({equity_actual:.2f}). "
                "Reinicializando métricas."
            )
            estado_dia = _recalibrar_baseline(equity_actual, params, motivo_corrupto)
            baseline_previo_valido = True
            estado_previo = estado_dia
    if estado_dia is None:
        estado_dia = actualizar_estado_dia(equity_actual, params=params)
    equity_ini = _to_float(estado_dia.get("equity_inicio_dia")) or 0.0
    equity_max = _to_float(estado_dia.get("equity_max_dia")) or 0.0

    if equity_ini <= 0:
        equity_ini = equity_actual if equity_actual > 0 else 1.0

    pnl_diario = float(equity_actual) - float(equity_ini)
    pnl_pct = (pnl_diario / float(equity_ini)) * 100.0 if float(equity_ini) > 0 else 0.0
    dd_max_pct = ((float(equity_actual) - float(equity_max)) / float(equity_max)) * 100.0 if float(equity_max) > 0 else 0.0

    fuente_tag = str(fuente_equity or "TOTAL").strip().upper()
    print(
        f"RIESGO DIARIO: equity_actual={equity_actual:.2f} | baseline={equity_ini:.2f} | "
        f"pct={pnl_pct:.2f}% | fuente={fuente_tag}"
    )

    if flag_reset:
        motivo_reset = f"RESET DIARIO manual: tmp/reset_dia.flag detectado. Baseline forzado a {equity_actual:.2f}."
        print(f"RIESGO DIARIO: {motivo_reset}")
        return True, motivo_reset, "ACTIVO"

    if not baseline_previo_valido:
        motivo_base = (
            "BASELINE DIARIO NO DEFINIDA (fecha distinta o cuenta virgen). "
            "Se fija al equity actual y no se dispara ningún stop."
        )
        print(f"RIESGO DIARIO: {motivo_base}")
        return True, motivo_base, "ACTIVO"

    # Parámetros (en %)
    # Parámetros (en %)
    soft_pct = 99999.0 # _to_float(params.get("daily_loss_soft_pct"))
    hard_pct = 99999.0 # _to_float(params.get("daily_loss_hard_pct"))
    cooldown_min = 1.0 # _to_float(params.get("cooldown_min"))

    # MODIFICACIÓN USUARIO: "NO QUIERO LIMITACIONES"
    # Forzamos limpieza de cualquier bloqueo previo para reactivación inmediata
    if bool(data.get("hard_pausa_dia")) or data.get("cooldown_hasta_ts", 0) > 0:
        print("🔓 DESBLOQUEO FORZADO (MODO SIN LIMITES): Limpiando PAUSA_RIESGO antigua.")
        data["hard_pausa_dia"] = False
        data["motivo_pausa"] = None
        data["cooldown_hasta_ts"] = 0.0
        _guardar_persistencia(data)

    now = float(time.time())

    # 1) Cooldown activo (Neutralizado)
    cooldown_hasta = 0.0
    
    # 4) OK: limpiar motivo y dejar activo
    data["cooldown_hasta_ts"] = 0.0
    data["hard_pausa_dia"] = False
    data["motivo_pausa"] = None
    _guardar_persistencia(data)

    return True, f"OK | PnL diario: {pnl_pct:.2f}% | DD máx: {dd_max_pct:.2f}% | Equity: {equity_actual:.2f}", "ACTIVO"

def forzar_bloqueo(motivo):
    """Bloquea el sistema manualmente (ej. fallo de auditoría)."""
    params = _cargar_parametros_activos()
    data = _cargar_persistencia(params=params)
    data["bloqueo_manual"] = str(motivo)
    _guardar_persistencia(data)
    return False, str(motivo), "BLOQUEADO"
