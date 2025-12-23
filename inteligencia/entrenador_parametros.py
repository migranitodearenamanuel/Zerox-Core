import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

# RUTAS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_OPERACIONES = os.path.join(BASE_DIR, "operaciones")
RUTA_PARAMETROS = os.path.join(BASE_DIR, "parametros_activos.json")
RUTA_LOG_APRENDIZAJE = os.path.join(os.path.dirname(BASE_DIR), "tmp", "zerox_aprendizaje.log")
RUTA_REPORTE_DIARIO = os.path.join(os.path.dirname(BASE_DIR), "tmp", "reporte_entrenador_diario.md")
RUTA_HISTORICO = os.path.join(RUTA_OPERACIONES, "historico_entrenador.json")
DIR_CHECKPOINTS = os.path.join(RUTA_OPERACIONES, "checkpoints_parametros")


def _now_iso() -> str:
    return datetime.now().isoformat()


def _leer_json(path: str, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        return default
    return default


def _guardar_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def cargar_parametros() -> Dict[str, Any]:
    params = _leer_json(RUTA_PARAMETROS, default={})
    if not isinstance(params, dict):
        params = {}

    # Defaults iniciales (compatibilidad)
    params.setdefault("k_atr_mult", 1.5)
    params.setdefault("r_reward_mult", 1.0)
    params.setdefault("riesgo_base_pct", 1.0)
    params.setdefault("version", "1.0.0")

    # Límites duros
    riesgo = params.get("riesgo") if isinstance(params.get("riesgo"), dict) else {}
    riesgo.setdefault("riesgo_min_pct", 0.25)
    riesgo.setdefault("riesgo_max_pct", 2.0)
    params["riesgo"] = riesgo

    apal = params.get("apalancamiento") if isinstance(params.get("apalancamiento"), dict) else {}
    apal.setdefault("leverage_max", 25)
    apal.setdefault("liq_buffer", 0.8)
    params["apalancamiento"] = apal

    return params


def guardar_parametros(params: Dict[str, Any]):
    _guardar_json(RUTA_PARAMETROS, params)


def registrar_aprendizaje(mensaje: str):
    linea = f"[{_now_iso()}] {mensaje}\n"
    try:
        os.makedirs(os.path.dirname(RUTA_LOG_APRENDIZAJE), exist_ok=True)
        with open(RUTA_LOG_APRENDIZAJE, "a", encoding="utf-8") as f:
            f.write(linea)
    except Exception:
        pass
    print(mensaje)


def _extraer_trades_pnl() -> List[float]:
    """
    Intenta leer PnL real desde archivos JSON de operaciones (si existen).
    Formato esperado: {"pnl_real": ...}
    """
    trades: List[float] = []
    if not os.path.exists(RUTA_OPERACIONES):
        return trades

    for root, _, files in os.walk(RUTA_OPERACIONES):
        for name in files:
            if not name.endswith(".json"):
                continue
            if name in ("historico_entrenador.json",):
                continue
            path = os.path.join(root, name)
            try:
                data = _leer_json(path, default=None)
                if not isinstance(data, dict):
                    continue
                if "pnl_real" in data:
                    trades.append(float(data["pnl_real"]))
            except Exception:
                continue
    return trades


def analizar_metrics() -> Optional[Dict[str, Any]]:
    """
    Métricas mínimas:
    - winrate
    - expectancy (media PnL)
    - profit factor
    - max drawdown (sobre equity_curve de PnL)
    """
    trades = _extraer_trades_pnl()
    if not trades:
        return None

    total = len(trades)
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]

    winrate = len(wins) / total if total > 0 else 0.0
    expectancy = float(np.mean(trades)) if trades else 0.0

    gross_profit = float(sum(wins))
    gross_loss = float(abs(sum(losses)))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999.0

    equity_curve = np.cumsum(trades)
    running_max = np.maximum.accumulate(equity_curve)
    drawdown = running_max - equity_curve
    max_dd = float(np.max(drawdown)) if len(drawdown) > 0 else 0.0

    return {
        "total_trades": int(total),
        "winrate": float(winrate),
        "expectancy": float(expectancy),
        "profit_factor": float(profit_factor),
        "max_dd": float(max_dd),
    }


def _ema(actual: float, objetivo: float, alpha: float) -> float:
    return float((1 - alpha) * actual + alpha * objetivo)


def _clamp(x: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, x)))


def _cargar_historico() -> List[Dict[str, Any]]:
    hist = _leer_json(RUTA_HISTORICO, default=[])
    return hist if isinstance(hist, list) else []


def _guardar_historico(hist: List[Dict[str, Any]]):
    _guardar_json(RUTA_HISTORICO, hist)


def _guardar_checkpoint(params: Dict[str, Any], etiqueta: str):
    os.makedirs(DIR_CHECKPOINTS, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(DIR_CHECKPOINTS, f"checkpoint_{etiqueta}_{ts}.json")
    _guardar_json(path, params)
    return path


def _revertir_a_ultimo_checkpoint() -> Optional[Dict[str, Any]]:
    if not os.path.exists(DIR_CHECKPOINTS):
        return None
    archivos = [f for f in os.listdir(DIR_CHECKPOINTS) if f.endswith(".json")]
    if not archivos:
        return None
    archivos.sort()
    path = os.path.join(DIR_CHECKPOINTS, archivos[-1])
    params = _leer_json(path, default=None)
    return params if isinstance(params, dict) else None


def generar_reporte_diario(metrics: Optional[Dict[str, Any]], params: Dict[str, Any], cambios: Optional[Dict[str, Any]] = None, nota: str = ""):
    os.makedirs(os.path.dirname(RUTA_REPORTE_DIARIO), exist_ok=True)

    lineas = []
    lineas.append(f"# Reporte diario — Entrenador de parámetros (ZEROX)")
    lineas.append("")
    lineas.append(f"- Fecha: {_now_iso()}")
    if nota:
        lineas.append(f"- Nota: {nota}")
    lineas.append("")

    lineas.append("## Métricas")
    if not metrics:
        lineas.append("- Estado: DATA_INSUFICIENTE (no hay `pnl_real` en operaciones)")
    else:
        lineas.append(f"- Trades: {metrics['total_trades']}")
        lineas.append(f"- Winrate: {metrics['winrate']*100:.1f}%")
        lineas.append(f"- Expectancy (media PnL): {metrics['expectancy']:.4f}")
        lineas.append(f"- Profit Factor: {metrics['profit_factor']:.2f}")
        lineas.append(f"- Max Drawdown (PnL acumulado): {metrics['max_dd']:.4f}")
    lineas.append("")

    lineas.append("## Parámetros activos")
    lineas.append(f"- riesgo_base_pct: {params.get('riesgo_base_pct')}")
    lineas.append(f"- k_atr_mult: {params.get('k_atr_mult')}")
    lineas.append(f"- r_reward_mult: {params.get('r_reward_mult')}")
    lineas.append("")

    if cambios:
        lineas.append("## Cambios aplicados")
        for k, v in cambios.items():
            lineas.append(f"- {k}: {v}")
        lineas.append("")

    with open(RUTA_REPORTE_DIARIO, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas).strip() + "\n")


def auto_tunning():
    registrar_aprendizaje("ENTRENADOR: Iniciando ciclo de auto-mejora (suave, no destructivo)...")

    params = cargar_parametros()
    metrics = analizar_metrics()

    # Historial para anti-locura
    hist = _cargar_historico()
    hist.append({"ts": _now_iso(), "metrics": metrics, "params": {k: params.get(k) for k in ("riesgo_base_pct", "k_atr_mult", "r_reward_mult")}})
    hist = hist[-30:]  # conservar 30 entradas
    _guardar_historico(hist)

    if not metrics or metrics.get("total_trades", 0) < 15:
        generar_reporte_diario(metrics, params, nota="Sin cambios: data insuficiente (<15 trades).")
        registrar_aprendizaje("ENTRENADOR: DATA INSUFICIENTE (<15 trades). Manteniendo parámetros.")
        return

    # Anti-locura: si expectancy < 0 durante 3 ejecuciones seguidas, revertir.
    ult = [h for h in hist[-3:] if isinstance(h, dict)]
    if len(ult) == 3:
        exp_neg = all((h.get("metrics") or {}).get("expectancy", 0) < 0 for h in ult if h.get("metrics"))
        if exp_neg:
            prev = _revertir_a_ultimo_checkpoint()
            if prev:
                guardar_parametros(prev)
                generar_reporte_diario(metrics, prev, nota="REVERTIDO: expectancy negativa 3 ciclos seguidos.")
                registrar_aprendizaje("ENTRENADOR: REVERTIDO al último checkpoint estable (expectancy negativa 3 ciclos).")
                return

    # Objetivos deterministas (muy simples):
    # - Si winrate bajo => aflojar SL (subir k_atr_mult).
    # - Si winrate alto + PF alto => más RR (subir r_reward_mult).
    winrate = float(metrics["winrate"])
    pf = float(metrics["profit_factor"])

    k_actual = float(params.get("k_atr_mult", 1.5))
    rr_mult_actual = float(params.get("r_reward_mult", 1.0))
    riesgo_actual = float(params.get("riesgo_base_pct", 1.0))

    # Límites
    riesgo_min = float((params.get("riesgo") or {}).get("riesgo_min_pct", 0.25))
    riesgo_max = float((params.get("riesgo") or {}).get("riesgo_max_pct", 2.0))

    k_min, k_max = 1.0, 3.0
    rr_mult_min, rr_mult_max = 0.8, 1.25
    alpha = 0.05  # paso pequeño (EMA)

    cambios: Dict[str, Any] = {}

    # Ajuste k_atr_mult
    if winrate < 0.40:
        k_obj = min(3.0, k_actual * 1.10)
    elif winrate > 0.70:
        k_obj = max(1.0, k_actual * 0.95)
    else:
        k_obj = k_actual
    k_nuevo = _clamp(_ema(k_actual, k_obj, alpha), k_min, k_max)

    # Ajuste r_reward_mult (RR multiplicador)
    if pf > 2.0 and winrate >= 0.50:
        rr_obj = min(rr_mult_max, rr_mult_actual * 1.05)
    elif pf < 1.2:
        rr_obj = max(rr_mult_min, rr_mult_actual * 0.95)
    else:
        rr_obj = rr_mult_actual
    rr_mult_nuevo = _clamp(_ema(rr_mult_actual, rr_obj, alpha), rr_mult_min, rr_mult_max)

    # Ajuste riesgo_base_pct (muy suave)
    if winrate > 0.60 and pf > 1.5:
        riesgo_obj = min(riesgo_max, riesgo_actual * 1.02)
    elif winrate < 0.45 or pf < 1.1:
        riesgo_obj = max(riesgo_min, riesgo_actual * 0.98)
    else:
        riesgo_obj = riesgo_actual
    riesgo_nuevo = _clamp(_ema(riesgo_actual, riesgo_obj, alpha), riesgo_min, riesgo_max)

    # Aplicar si hay cambios reales
    if abs(k_nuevo - k_actual) > 1e-6:
        cambios["k_atr_mult"] = f"{k_actual:.3f} -> {k_nuevo:.3f}"
        params["k_atr_mult"] = round(k_nuevo, 3)
    if abs(rr_mult_nuevo - rr_mult_actual) > 1e-6:
        cambios["r_reward_mult"] = f"{rr_mult_actual:.3f} -> {rr_mult_nuevo:.3f}"
        params["r_reward_mult"] = round(rr_mult_nuevo, 3)
    if abs(riesgo_nuevo - riesgo_actual) > 1e-6:
        cambios["riesgo_base_pct"] = f"{riesgo_actual:.3f} -> {riesgo_nuevo:.3f}"
        params["riesgo_base_pct"] = round(riesgo_nuevo, 3)

    if cambios:
        # Guardar checkpoint si métricas están "sanas"
        if pf >= 1.5 and metrics["expectancy"] >= 0:
            ck = _guardar_checkpoint(params, etiqueta="estable")
            registrar_aprendizaje(f"ENTRENADOR: Checkpoint estable guardado en {ck}")

        params["version"] = datetime.now().strftime("%Y%m%d_%H%M")
        guardar_parametros(params)
        generar_reporte_diario(metrics, params, cambios=cambios, nota="Cambios aplicados (EMA suave).")
        registrar_aprendizaje(f"ENTRENADOR: Parámetros optimizados y guardados: {', '.join(cambios.keys())}")
    else:
        generar_reporte_diario(metrics, params, nota="Sin cambios: sistema equilibrado.")
        registrar_aprendizaje("ENTRENADOR: Sistema equilibrado. Sin cambios.")


if __name__ == "__main__":
    auto_tunning()

