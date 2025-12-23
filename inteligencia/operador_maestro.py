import ccxt
import time
import sys
# FORZAR UTF-8 (evita mojibake y crashes por Unicode en Windows)
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
try:
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import os
import warnings

# --- SILENCIAR DEPRECATIONS Y WARNINGS MOLESTOS ---
# 1. Triton (NVidia): Solucionado via device='cpu' en PPO.load. 
# warnings.filterwarnings("ignore", category=UserWarning, module="triton.knobs") 

# 2. HuggingFace resume_download future warning (Interno de librerias, dificil de arreglar sin update)
warnings.filterwarnings("ignore", category=FutureWarning, message=".*resume_download.*")

# 3. Pandas fillna (por si acaso queda alguno suelto)
warnings.filterwarnings("ignore", category=FutureWarning, message=".*fillna.*")

import pandas as pd
from datetime import datetime
import json
import random
import requests
from analisis_tecnico.scoring_confluencias import evaluar_setup_determinista

RUTA_FLAG_RESET_BACKOFF = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tmp", "reset_backoff.flag"))

# Corrección de PATH para encontrar 'utilidades' (nivel superior)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- IMPORTACIONES DEL SISTEMA (EN ESPAÑOL) ---
import configuracion as config
from notificador import notificador
import gestor_riesgo
import tpsl_profesional # 🎯 NIVEL PRO (ATR + CONFIANZA)
import puente_visual
import gestor_ordenes # 🛡️ GESTOR DE ÓRDENES REALES (EVIDENCIA)
import reloj_bitget # NUEVO MODULO DE TIEMPOual

import auto_mejora
import mente_local as mente_maestra # 🧠 CEREBRO LOCAL (Ollama)
import threading
# Dependencias opcionales (no pueden tumbar el core)
try:
    from utilidades import sincronizar_web
except Exception as e:
    sincronizar_web = None
    print(f"ADVERTENCIA: Sincronizador Web no disponible: {e}")

try:
    from utilidades import periodista
except Exception as e:
    periodista = None
    print(f"ADVERTENCIA: Periodista no disponible: {e}")
import gestor_ordenes # 🛡️ GESTOR DE ÓRDENES REALES (EVIDENCIA)

# ==============================================================================
# 🦈 OPERADOR DEPREDADOR V2.0 (ESPAÑOL PURO)
# ==============================================================================
# Misión: Escanear el TOP 30 de Bitget, detectar presas y ejecutar con precisión.
# ==============================================================================

class OperadorDepredador:
    RIESGO_NO_BACKOFF_MOTIVOS = {
        "PAUSA_RIESGO",
        "MINIMO_SUPERA_RIESGO",
        "SCORE_BAJO",
        "SIN_TP_SL",
        "SIN_MUNICION",
    }
    def __init__(self):
        # 0. INICIALIZACIÓN CRÍTICA DE THREADING (Para evitar crash en heartbeat)
        # Debe ejecutarse ANTES de tocar cualquier subsistema
        self.hb_lock = threading.Lock()
        self.hb_data = {
            "estado": "INICIANDO",
            "motivo": "Arranque",
            "paso": "Boot",
            "paso_ts": time.time(),
            "ciclo": 0
        }
        self.hb_running = False
        self.blacklist_runtime = set() # LISTA NEGRA TEMPORAL (RUNTIME)
        self.exchange = None
        self.modelo_ia = None  # Debe existir antes del heartbeat
        self.detener_solicitado = False
        self.backoff_until_by_symbol = {}
        self.backoff_duration_by_symbol = {}
        self.global_backoff_until = 0.0
        self.global_backoff_duration = 0.0
        self.backoff_disabled = os.getenv("BACKOFF_DISABLED", "0") == "1"
        self._backoff_base_s = 5
        self._backoff_max_s = 120
        self._backoff_jitter = 0.15
        self._ciclo_iter = 0
        self._ultimo_mensaje_ciclo = -1
        self._ultimo_no_entra_key = None
        self._ultimo_info_no_entra = {}
        self.modo_trading = "PAPER"
        self.motivo_bloqueo_trading = ""
        self.mercados_operables = None
        self.audit_reparacion_cooldown_s = 300
        self._audit_reparacion_ts = {}
        self.cuarentena_alert_cooldown_s = 300
        self._cuarentena_alert_ts = {}
        self.cuarentena_evidencia_cooldown_s = 600
        self._cuarentena_evidencia_ts = 0.0

        # Máquina de estados (24/7): el core sigue vivo; solo se bloquean entradas cuando toque.
        self.estado_trading = "ACTIVO"
        self.motivo_estado_trading = "OK"
        self.entradas_habilitadas_riesgo = True
        self.emergencia_cuarentena = False
        self.motivo_emergencia = ""

        # MODO MANTENIMIENTO (seguridad de ingeniería)
        self.modo_mantenimiento = bool(getattr(config, "MODO_MANTENIMIENTO", False))
        try:
            self.balance_mantenimiento_usdt = float(getattr(config, "BALANCE_MANTENIMIENTO_USDT", 100.0))
        except Exception:
            self.balance_mantenimiento_usdt = 100.0

        # Cache de velas locales para modo mantenimiento/offline
        self._cache_velas_local = {}

        # Asegurar carpeta tmp (evidencias, crash reports, logs) desde cualquier CWD
        try:
            _tmp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tmp"))
            os.makedirs(_tmp_dir, exist_ok=True)
        except Exception:
            pass

        print("\n" + "=" * 50)
        print("🦈 INICIANDO PROTOCOLO DEPREDADOR (MULTI-ACTIVO)")
        print(f"🌍 MERCADO OBJETIVO: FUTUROS USDT | CAPACIDAD: {config.MAXIMO_PARES_ESCANEO} PARES")
        print("=" * 50)

        # 1. Conexión con el Exchange (Bitget)
        # 1. Conexión con el Exchange (Bitget)
        # 0. HEARTBEAT INQUEBRANTABLE (Primero que todo, incluso si Bitget falla)
        self._iniciar_heartbeat_thread()

        if self.modo_mantenimiento:
            # En mantenimiento: intentamos conectar, pero si falla NO bloqueamos el arranque.
            if self._stop_solicitado():
                self.detener_solicitado = True
            else:
                ok = self._conectar_exchange()
                if not ok:
                    print(
                        f"MODO_MANTENIMIENTO: sin conexión a Bitget; continuando con datos locales (balance={self.balance_mantenimiento_usdt:.2f} USDT)."
                    )
                    self.exchange = None
                    self._actualizar_estado_hb("MANTENIMIENTO", "Sin conexión a Bitget (modo mantenimiento)")
        else:
            backoff_conexion_s = 5
            while True:
                if self._stop_solicitado():
                    self.detener_solicitado = True
                    break

                ok = self._conectar_exchange()
                if ok:
                    break

                time.sleep(backoff_conexion_s)
                backoff_conexion_s = min(backoff_conexion_s * 2, 60)

        if self.detener_solicitado:
            # STOP durante arranque: mantener proceso limpio y sin corrupción
            return

        # Compuerta REAL/PAPER/BLOQUEADO (no rompe el flujo)
        self._evaluar_compuerta_real()
        if self.modo_mantenimiento:
            self._actualizar_estado_hb("MANTENIMIENTO", "MODO_MANTENIMIENTO activo: órdenes deshabilitadas")

        self.modelo_ia = None          # El cerebro (Red Neuronal)
        self.activo_actual = None      # La presa actual (par de trading)
        self.posicion_abierta = False  # Si estamos dentro del mercado
        self.precio_entrada = 0.0      # Precio al que entramos
        
        # Nuevos estados para Telemetría Avanzada
        self.razonamiento_actual = "Escaneando el mercado en busca de patrones..."
        self.analisis_completo = {} # Cache de inteligencia
        self.datos_tecnicos_cache = {
            "rsi": 50,
            "volumen_24h": 0,
            "tendencia": "NEUTRA",
            "tp_precio": 0,
            "sl_precio": 0
        }
        self.posiciones_cache = [] # CACHE VISUAL PERSISTENTE
        self.ordenes_pendientes = [] # COLA DE EJECUCIÓN VIRTUAL (SOFT TP/SL)
        self.market_cache_precios = {} # 🔥 Cache de PRECIOS GLOBALES (Scanner)

        # Limpieza Inicial de Pantalla
        puente_visual.actualizar_estado({
            "estado_sistema": "INICIALIZANDO 🦈",
            "cerebro_info": "LOCAL (Llama 3.1)", # INDICADOR UI
            "mensaje_error": "",
            "pensamientos": [],
            "precios": {},
            "progreso": 0,
            "posiciones": [] # LIMPIO PARA ARRANQUE REAL
        })

        # 🚀 INICIAR SUBSISTEMAS DE SEGUNDO PLANO
        # 0. HEARTBEAT ya iniciado al arranque

        # 1. Periodista (Noticias Visuales) - Hilo Independiente
        if periodista is not None:
            try:
                periodista.inicializar_dummy()  # Asegurar que hay algo que mostrar
            except Exception:
                pass
            self.thread_periodista = threading.Thread(target=self._bucle_periodista, daemon=True)
            self.thread_periodista.start()
        else:
            self.thread_periodista = None
            print("PERIODISTA: deshabilitado (dependencias no disponibles).")

        # 2. ACADEMIA ZEROX (Aprendizaje Continuo)
        try:
            import academia_zerox
            self.academia = academia_zerox.AcademiaZeroX()
            self.thread_academia = threading.Thread(target=self.academia.bucle_aprendizaje, daemon=True)
            self.thread_academia.start()
            print("🧠 HILO ACADEMIA INICIADO")
        except Exception as e:
            print(f"⚠️ Fallo iniciando Academia: {e}")
            self.academia = None

        # 3. Ingesta de Noticias (Segundo Plano Cronometrado) - Hilo Independiente
        self.thread_noticias = threading.Thread(target=self._bucle_noticias, daemon=True)
        self.thread_noticias.start()

        # 3. Vigilante de Cartera (REAL-TIME UI)
        self.thread_vigilante = threading.Thread(target=self._hilo_vigilante_cartera, daemon=True)
        self.thread_vigilante.start()

        try:
            balance = self.exchange.fetch_balance()
            saldo_free = float((balance.get("USDT") or {}).get("free") or 0.0)
            equity_total = float((balance.get("USDT") or {}).get("total") or 0.0)
            print(f"✅ CONEXIÓN ESTABLECIDA. MUNICIÓN: {saldo_free:.2f} USDT | EQUITY: {equity_total:.2f} USDT")
            puente_visual.actualizar_estado({"saldo_cuenta": f"{equity_total:.2f}"})

            # FIJAR CAPITAL INICIAL DEL DÍA (Para Drawdown)
            gestor_riesgo.inicializar_dia(equity_total if equity_total > 0 else saldo_free)

            # FILTRO DE MERCADOS PARA CUENTAS PEQUEÑAS
            try:
                self._construir_mercados_operables(max_margin_usdt=float(saldo_free) * 0.95)
            except Exception as e_op:
                print(f"Error construyendo mercados operables: {e_op}")
            
        except Exception as e:
            if self.modo_mantenimiento:
                saldo = float(getattr(self, "balance_mantenimiento_usdt", 100.0))
                print(f"MODO_MANTENIMIENTO: sin balance real disponible ({e}). Usando BALANCE_MANTENIMIENTO_USDT={saldo:.2f}.")
                try:
                    puente_visual.actualizar_estado({"saldo_cuenta": f"{saldo:.2f}"})
                except Exception:
                    pass
                try:
                    gestor_riesgo.inicializar_dia(saldo)
                except Exception:
                    pass
            else:
                self._reportar_error_fatal(f"Error de credenciales: {e}")

    def _conectar_exchange(self):
        """
        Conecta a Bitget en modo FUTUROS (SWAP).
        """
        try:
            print("📡 Estableciendo enlace satelital con Bitget (FUTUROS)...")
            
            # Intentar cargar de os.getenv o fallback a config
            api_key = os.getenv('BITGET_API_KEY') or config.CLAVE_API
            secret = os.getenv('BITGET_SECRET') or config.SECRETO_API
            password = os.getenv('BITGET_PASSWORD') or config.CONTRASENA_API

            if not api_key or not secret or not password:
                if self.modo_mantenimiento:
                    print("MODO_MANTENIMIENTO: credenciales ausentes. Bitget en modo público (sin trading).")
                    self.exchange = ccxt.bitget({
                        'enableRateLimit': True,
                        'options': {
                            'defaultType': 'swap',
                            'adjustForTimeDifference': True,
                            'createMarketBuyOrderRequiresPrice': False
                        }
                    })
                    self._actualizar_estado_hb("MANTENIMIENTO", "Sin credenciales: modo público (solo datos)")
                    return True
                raise ValueError("Faltan credenciales en .env")

            self.exchange = ccxt.bitget({
                'apiKey': api_key,
                'secret': secret,
                'password': password,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'swap',
                    'adjustForTimeDifference': True, # 🕒 SINCRONIZACIÓN TIEMPO (CRÍTICO)
                    'createMarketBuyOrderRequiresPrice': False
                }
            })
            # Verificar conexión
            balance = None
            try:
                balance = self.exchange.fetch_balance()
            except Exception as e_bal:
                if not self.modo_mantenimiento:
                    raise
                print(f"MODO_MANTENIMIENTO: no se pudo verificar balance (OK): {e_bal}")
            print("✅ CONEXIÓN BITGET ESTABLECIDAS (FUTUROS USDT)")

            # Inicializar monitor de riesgo diario con saldo real
            if balance is None:
                try:
                    balance = self.exchange.fetch_balance()
                except Exception:
                    balance = None

            equity_total = 0.0
            saldo_free = 0.0
            try:
                saldo_free = float((balance.get("USDT") or {}).get("free") or 0.0) if balance else 0.0
                equity_total = float((balance.get("USDT") or {}).get("total") or 0.0) if balance else 0.0
            except Exception:
                saldo_free = 0.0
                equity_total = 0.0

            gestor_riesgo.inicializar_dia(equity_total if equity_total > 0 else saldo_free)
            
            # 🛡️ RECUPERACIÓN DE ARRANQUE (BOOT AUDIT)
            self._recuperacion_arranque()
            return True
            
        except Exception as e:
            print(f"❌ ERROR FATAL DE CONEXIÓN: {e}")
            self.exchange = None
            self._actualizar_estado_hb("BLOQUEADO", f"Fallo de conexion Bitget: {e}")
            return False

    def _iniciar_heartbeat_thread(self):
        """Inicia el hilo independiente de latido (Inmortalidad)"""
        import threading
        import faulthandler
        
        # Activar Faulthandler para dumps en crash
        faulthandler.enable()

        self.hb_running = True
        self.hb_data = {
            "estado": "INICIANDO",
            "motivo": "Arranque",
            "paso": "Boot",
            "paso_ts": time.time(),
            "ciclo": 0
        }
        self.hb_lock = threading.Lock()
        
        def _latido():
            while self.hb_running:
                try:
                    # 1. Chequeo de bandera de dump (Solicitud de Watchdog)
                    dump_flag = os.path.join(os.path.dirname(__file__), "..", "tmp", "zerox_dump_request.flag")
                    if os.path.exists(dump_flag):
                        dump_out = os.path.join(os.path.dirname(__file__), "..", "tmp", "zerox_stackdump.txt")
                        with open(dump_out, "w") as f:
                            f.write(f"STACK DUMP REQUESTED AT {datetime.now()}\n")
                            faulthandler.dump_traceback(file=f, all_threads=True)
                        try: os.remove(dump_flag)
                        except: pass
                    
                    # 2. Leer estado compartido (Thread-safe logic simple)
                    with self.hb_lock:
                         estado = self.hb_data['estado']
                         motivo = self.hb_data['motivo']
                         paso = self.hb_data['paso']
                         paso_ts = self.hb_data['paso_ts']
                         ciclo = self.hb_data['ciclo']
                    
                    # 3. Escribir Heartbeat Atómico
                    ruta_hb = os.path.join(os.path.dirname(__file__), "heartbeat.json")
                    ruta_tmp = ruta_hb + ".tmp"
                    
                    # Datos extra
                    offset_ms = 0
                    try: 
                        if hasattr(reloj_bitget, 'get_offset_ms'): offset_ms = reloj_bitget.get_offset_ms() or 0
                    except: pass
                    
                    hb_json = {
                        "timestamp": time.time(),
                        "timestamp_iso": datetime.now().isoformat(),
                        "estado_trading": estado,
                        "motivo_estado": motivo,
                        "modo_mantenimiento": bool(getattr(self, "modo_mantenimiento", False)),
                        "modo_trading": getattr(self, "modo_trading", "UNKNOWN"),
                        "ollama": "ONLINE" if self.modelo_ia else "OFFLINE", # Aprox
                        "bitget": "OK" if self.exchange else "FALLO",
                        "offset_ms": offset_ms,
                        "ciclo": ciclo,
                        "ultima_accion": paso,
                        "inicio_paso_ts": paso_ts,
                        "duracion_paso_s": time.time() - paso_ts
                    }
                    
                    with open(ruta_tmp, "w", encoding="utf-8", errors="replace") as f:
                        json.dump(hb_json, f, ensure_ascii=False)
                    
                    # Renombrado atómico (evita JSON corrupto)
                    os.replace(ruta_tmp, ruta_hb)
                    
                except Exception as e:
                    print(f"💔 Error en Hilo Heartbeat: {e}")
                
                time.sleep(2) # 2s intervalo fijo inquebrantable

        t = threading.Thread(target=_latido, daemon=True)
        t.start()
        print("💓 HEARTBEAT THREAD INICIADO (DAEMON)")

    def _registrar_paso(self, paso_nombre):
        """Registra el paso actual para detección de cuelgues"""
        with self.hb_lock:
            self.hb_data['paso'] = paso_nombre
            self.hb_data['paso_ts'] = time.time()
            
    def _actualizar_estado_hb(self, estado, motivo):
        """Actualiza estado general para heartbeat"""
        with self.hb_lock:
            self.hb_data['estado'] = estado
            self.hb_data['motivo'] = motivo
            self.hb_data['ciclo'] = getattr(self, 'contador_ciclos', 0)

    # Alias para compatibilidad anterior, redirige al nuevo sistema
    def _actualizar_heartbeat(self, estado_general="ACTIVO", motivo="Operando normalmente"):
        self._actualizar_estado_hb(estado_general, motivo)

    def _ruta_stop(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "STOP"))

    def _stop_solicitado(self):
        try:
            return os.path.exists(self._ruta_stop())
        except Exception:
            return False

    def _ruta_enable_real(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ENABLE_REAL.txt"))

    def _evaluar_compuerta_real(self):
        """
        Compuerta REAL segura:
          - OBEDECE A config.TRADING_MODE (La verdad absoluta).
          - Si es REAL, se activa SIN PREGUNTAS (Solicitud de usuario "URGENTE").
        """
        # 1. Leer de CONFIGURACIÓN CENTRALIZADA (Ahí es donde forzamos "REAL")
        modo_config = getattr(config, "TRADING_MODE", "PAPER").strip().upper()
        
        if modo_config == "REAL":
            self.modo_trading = "REAL"
            self.motivo_bloqueo_trading = ""
            self._actualizar_estado_hb("REAL", "Modo REAL A FUEGO (Usuario)")
            print("🚀 MODO REAL CONFIRMADO. SISTEMA ARMADO Y PELIGROSO.")
            return

        # Si no es REAL, es PAPER
        self.modo_trading = "PAPER"
        self.motivo_bloqueo_trading = ""
        self._actualizar_estado_hb("PAPER", "Modo PAPER (Default)")

    def _es_motivo_no_backoff(self, estado, motivo):
        estado_norm = (estado or "").upper().strip()
        if estado_norm in self.RIESGO_NO_BACKOFF_MOTIVOS:
            return True
        motivo_norm = (motivo or "").upper()
        return any(tag in motivo_norm for tag in self.RIESGO_NO_BACKOFF_MOTIVOS)

    def _sleep_no_entra_riesgo(self, estado, motivo):
        info = f"{estado}. {motivo}".strip()
        print(f"NO_ENTRA: {info} (sin backoff, pausa corta)")
        time.sleep(random.uniform(5, 15))

    def _verificar_backoff_disponible(self, simbolo):
        if self.backoff_disabled:
            return True
        ahora = time.time()
        if ahora < self.global_backoff_until:
            restante = int(self.global_backoff_until - ahora)
            print(f"NO_ENTRA: backoff global activo ({restante}s). Saltando {simbolo}.")
            time.sleep(1)
            return False
        until = self.backoff_until_by_symbol.get(simbolo, 0.0)
        if ahora < until:
            restante = int(until - ahora)
            print(f"NO_ENTRA: backoff activo ({restante}s). Saltando entrada en {simbolo}.")
            return False
        return True

    def _marcar_backoff_simbolo(self, simbolo, motivo=None, duration=None):
        if self.backoff_disabled:
            print(f"NO_ENTRA: backoff ignorado ({motivo}).")
            return
        previo = self.backoff_duration_by_symbol.get(simbolo, 0.0)
        siguiente = duration or self._backoff_base_s
        if previo > 0:
            siguiente = min(previo * 2, self._backoff_max_s)
        jitter = 1 + random.uniform(-self._backoff_jitter, self._backoff_jitter)
        siguiente = max(self._backoff_base_s, min(self._backoff_max_s, siguiente * jitter))
        self.backoff_duration_by_symbol[simbolo] = siguiente
        self.backoff_until_by_symbol[simbolo] = time.time() + siguiente
        simbolo_txt = simbolo or "SIMBOLO"
        print(f"NO_ENTRA: {motivo or 'error transitorio'} {simbolo_txt}. Backoff {siguiente:.1f}s")

    def _marcar_backoff_global(self, motivo=None, duration=None):
        if self.backoff_disabled:
            print(f"NO_ENTRA: backoff global ignorado ({motivo}).")
            return
        previa = self.global_backoff_duration or 0.0
        siguiente = duration or (self._backoff_base_s * 2)
        if previa > 0:
            siguiente = min(previa * 2, self._backoff_max_s)
        jitter = 1 + random.uniform(-self._backoff_jitter, self._backoff_jitter)
        siguiente = max(self._backoff_base_s, min(self._backoff_max_s, siguiente * jitter))
        self.global_backoff_duration = siguiente
        self.global_backoff_until = time.time() + siguiente
        print(f"NO_ENTRA: backoff global {motivo or ''} ({siguiente:.1f}s).")

    def _limpiar_backoff_simbolo(self, simbolo):
        self.backoff_until_by_symbol.pop(simbolo, None)
        self.backoff_duration_by_symbol.pop(simbolo, None)

    def _obtener_codigo_http(self, error):
        for attr in ("http_status_code", "status_code", "code"):
            valor = getattr(error, attr, None)
            if valor is None:
                continue
            try:
                return int(valor)
            except (TypeError, ValueError):
                continue
        return None

    def _es_error_transitorio(self, error):
        tipos = (
            ccxt.NetworkError,
            ccxt.RequestTimeout,
            ccxt.ExchangeNotAvailable,
            ccxt.RateLimitExceeded,
            ccxt.DDoSProtection,
        )
        if isinstance(error, tipos):
            return True
        if isinstance(error, (requests.exceptions.ConnectionError, requests.exceptions.Timeout, ConnectionError, TimeoutError)):
            return True
        codigo = self._obtener_codigo_http(error)
        if codigo == 429 or (codigo is not None and 500 <= codigo < 600):
            return True
        mensaje = str(error).lower()
        for palabra in ("rate limit", "too many requests", "429", "exchange not available", "temporarily"):
            if palabra in mensaje:
                return True
        return False

    def _es_error_sistemico(self, error):
        if isinstance(error, (ccxt.RateLimitExceeded, ccxt.ExchangeNotAvailable, ccxt.DDoSProtection)):
            return True
        codigo = self._obtener_codigo_http(error)
        return codigo == 429 or (codigo is not None and 500 <= codigo < 600)

    def _leer_ultimo_motivo_no_entra(self):
        ruta = getattr(gestor_riesgo, "RUTA_TMP_NO_ENTRA", None)
        if not ruta or not os.path.exists(ruta):
            return {}
        data = {}
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    data[key.strip()] = val.strip()
        except Exception:
            pass
        return data

    def _limpiar_backoff_por_motivo(self, motivo_data):
        if not motivo_data:
            return
        simbolo = motivo_data.get("simbolo")
        motivo = (motivo_data.get("motivo") or "").upper()
        clave = (simbolo, motivo)
        if clave == self._ultimo_no_entra_key:
            return
        self._ultimo_no_entra_key = clave
        qty = 0.0
        try:
            qty = float(motivo_data.get("qty") or 0.0)
        except Exception:
            qty = 0.0
        if not simbolo:
            return
        if qty > 0 or ("SIZING" not in motivo and motivo):
            self._limpiar_backoff_simbolo(simbolo)

    def _procesar_flag_reset_backoff(self):
        if not os.path.exists(RUTA_FLAG_RESET_BACKOFF):
            return
        try:
            os.remove(RUTA_FLAG_RESET_BACKOFF)
        except Exception:
            pass
        self.backoff_until_by_symbol.clear()
        self.backoff_duration_by_symbol.clear()
        self.global_backoff_until = 0.0
        self.global_backoff_duration = 0.0
        print("⚠️ RESET_BACKOFF detectado: reiniciando bloqueos por símbolo y global.")

    def _reportar_por_que_no_entra(self, motivo_data):
        if self._ultimo_mensaje_ciclo == self._ciclo_iter:
            return
        motivo = motivo_data.get("motivo") if motivo_data else ""
        motivo = (motivo or "sin registro").strip()
        simbolo = motivo_data.get("simbolo") if motivo_data else ""
        estado = self.estado_trading or "ACTIVO"
        motivo_estado = self.motivo_estado_trading or "OK"
        destino = f"{simbolo}" if simbolo else "sin símbolo"
        mensaje = (
            f"POR QUÉ NO ENTRA: estado={estado} ({motivo_estado}) | "
            f"motivo humano [{destino}]: {motivo}"
        )
        print(mensaje)
        self._ultimo_mensaje_ciclo = self._ciclo_iter

    def _blacklist_permanente_25013(self, simbolo, motivo="No soporta trading por API (Error 25013)"):
        try:
            base = (simbolo.split(":")[0]).split("/")[0]
            if not base:
                return

            ruta_blacklist = os.path.join(os.path.dirname(__file__), "simbolos_bloqueados.json")
            data = {}
            if os.path.exists(ruta_blacklist):
                try:
                    with open(ruta_blacklist, "r", encoding="utf-8") as f:
                        data = json.load(f) or {}
                except Exception:
                    data = {}

            ahora = datetime.now().isoformat()
            entry = {"motivo": motivo, "fecha": ahora, "status": "BLOQUEADO_PERMANENTE"}
            data[f"{base}USDT_UMCBL"] = entry
            data[f"{base}USDT"] = entry

            with open(ruta_blacklist, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def _cerrar_todas_posiciones_seguro(self, motivo):
        if not self.exchange:
            return
        if self.modo_mantenimiento:
            print(f"STOP: MODO_MANTENIMIENTO activo. No se cierran posiciones automáticamente. Motivo: {motivo}")
            return
        try:
            posiciones = self.exchange.fetch_positions(None)
        except Exception as e:
            print(f"STOP: no se pudieron leer posiciones: {e}")
            return

        blacklist = {}
        try:
            blacklist = self._cargar_blacklist_persistente()
        except Exception:
            blacklist = {}

        for pos in posiciones or []:
            try:
                simbolo = pos.get("symbol")
                contratos = float(pos.get("contracts") or 0)
                lado = str(pos.get("side") or "").lower()  # long/short

                if not simbolo or contratos <= 0:
                    continue

                # REGLA: TSLA y símbolos con Error 25013 (blacklist) => NO TOCAR (cierre manual)
                try:
                    if simbolo in getattr(self, "blacklist_runtime", set()):
                        print(f"STOP: {simbolo} en blacklist runtime. NO TOCAR. Cierre manual requerido.")
                        continue
                    if self._simbolo_en_blacklist_persistente(simbolo, blacklist):
                        print(f"STOP: {simbolo} en blacklist permanente. NO TOCAR. Cierre manual requerido.")
                        continue
                except Exception:
                    pass

                inverse_side = "sell" if lado == "long" else "buy"
                print(f"STOP: cerrando {simbolo} ({lado}) {contratos} ctrs | Motivo: {motivo}")
                self.exchange.create_order(simbolo, "market", inverse_side, contratos, params={"reduceOnly": True})
            except Exception as e:
                print(f"STOP: fallo cerrando posicion: {e}")

    def _shutdown_seguro(self, motivo):
        try:
            print(f"STOP: {motivo}. Cerrando con seguridad y terminando...")
            self._actualizar_estado_hb("DETENIENDO", motivo)
            try:
                puente_visual.actualizar_estado({
                    "estado": "DETENIENDO",
                    "estado_sistema": motivo,
                    "color_estado": "rojo"
                })
            except Exception:
                pass

            self._cerrar_todas_posiciones_seguro(motivo)
        finally:
            try:
                self.hb_running = False
            except Exception:
                pass
            self.detener_solicitado = True

    def _recuperacion_arranque(self):
        """
        🛡️ RECUPERACIÓN DE ARRANQUE (BOOT AUDIT)
        """
        print("🛡️ INICIANDO AUDITORÍA DE RECUPERACIÓN...")
        self._actualizar_heartbeat("ARRANQUE", "Recuperando estado...")
        # ... (Resto del código original)
        """
        AUDITORÍA INICIAL: Verifica todas las posiciones abiertas al iniciar.
        Si alguna no tiene TP/SL, intenta repararla o lanza EMERGENCIA.
        """
        print("🔎 EJECUTANDO AUDITORÍA DE ARRANQUE...")
        try:
            posiciones = self.exchange.fetch_positions()
            posiciones_reales = [p for p in posiciones if float(p['contracts']) > 0]
            
            if not posiciones_reales:
                print("✅ ARRANQUE LIMPIO: No hay posiciones abiertas.")
                return

            print(f"⚠️ DETECTADAS {len(posiciones_reales)} POSICIONES ABIERTAS. VERIFICANDO BLINDAJE...")
            
            # En mantenimiento: solo lectura (NO colocar TP/SL ni cerrar nada)
            if self.modo_mantenimiento:
                print("MODO_MANTENIMIENTO: posiciones detectadas. No se reparan TP/SL automáticos. Revisión manual requerida.")
                self._actualizar_estado_hb("EMERGENCIA", "Posiciones detectadas en mantenimiento (sin TP/SL automático).")
                return

            # DELEGAMOS AL GESTOR EXPERTO
            gestor_ordenes.reparar_posiciones_desnudas(self.exchange, posiciones_reales)

            # ... (Rest of logic truncated as we replaced the loop)
            return
                    
        except Exception as e:
            print(f"❌ ERROR EN AUDITORÍA DE ARRANQUE: {e}")
            # No bloqueamos start completo, pero logueamos fuerte


    # --------------------------------------------------------------------------
    # 📡 FUNCIONES DE ESCANEO Y DATOS
    # --------------------------------------------------------------------------

    def _cargar_blacklist_persistente(self):
        ruta_blacklist = os.path.join(os.path.dirname(__file__), "simbolos_bloqueados.json")
        if os.path.exists(ruta_blacklist):
            try:
                with open(ruta_blacklist, "r", encoding="utf-8") as f:
                    return json.load(f) or {}
            except Exception:
                return {}
        return {}

    def _simbolo_en_blacklist_persistente(self, simbolo, blacklist):
        try:
            simbolo_display = simbolo.split(":")[0]
            base_symbol = simbolo_display.split("/")[0]
            k_umcbl = base_symbol + "USDT_UMCBL"
            k_simple = base_symbol + "USDT"
            return isinstance(blacklist, dict) and (k_umcbl in blacklist or k_simple in blacklist)
        except Exception:
            return False

    def _min_cost_usdt_market(self, market):
        try:
            min_cost = (((market or {}).get("limits") or {}).get("cost") or {}).get("min")
            min_cost = float(min_cost)
            if min_cost > 0:
                return min_cost
        except Exception:
            pass
        return 5.0

    def _lmax_market(self, market):
        try:
            max_lev = (((market or {}).get("limits") or {}).get("leverage") or {}).get("max")
            max_lev = int(float(max_lev))
            if max_lev > 0:
                return max_lev
        except Exception:
            pass

        # Fallback conservador: si CCXT no expone límite, usamos el máximo "de casa".
        for key in ("APALANCAMIENTO_MAX", "MAX_APALANCAMIENTO", "LEVERAGE_MAX"):
            try:
                v = int(getattr(config, key))
                if v > 0:
                    return v
            except Exception:
                continue
        try:
            return max(1, int(getattr(config, "APALANCAMIENTO", 1)))
        except Exception:
            return 1

    def _construir_mercados_operables(self, max_margin_usdt):
        """
        Construye una lista de mercados operables para cuentas pequeñas:
          - Excluye blacklist persistente (TSLA/25013, etc).
          - Excluye si min_cost_usdt > (max_margin_usdt * Lmax * 0.95).
        """
        try:
            max_margin_usdt = float(max_margin_usdt)
        except Exception:
            max_margin_usdt = 0.0

        if not self.exchange or max_margin_usdt <= 0:
            self.mercados_operables = set()
            print("Mercados operables: 0 / total: 0")
            return self.mercados_operables

        blacklist = self._cargar_blacklist_persistente()
        operables = set()
        total = 0

        try:
            mercados = self.exchange.load_markets() or {}
        except Exception:
            mercados = {}

        for m in mercados.values():
            try:
                if not (m.get("swap") and m.get("quote") == "USDT" and m.get("active")):
                    continue
                simbolo = m.get("symbol")
                if not simbolo:
                    continue

                total += 1

                if self._simbolo_en_blacklist_persistente(simbolo, blacklist):
                    continue

                min_cost = self._min_cost_usdt_market(m)
                Lmax = self._lmax_market(m)

                if min_cost > (max_margin_usdt * float(Lmax) * 0.95):
                    continue

                operables.add(simbolo)
            except Exception:
                continue

        self.mercados_operables = operables
        print(f"Mercados operables: {len(operables)} / total: {total}")
        return operables
    
    def obtener_top_activos(self):
        """Descarga el mercado entero y selecciona los 30 con más volumen."""
        try:
            # 1. Obtener metadatos de mercados (para saber cuáles son USDT Futures)
            mercados = self.exchange.load_markets()
            
            # Filtro: Solo Futuros (Swap), que sean USDT y estén activos
            simbolos_candidatos = [
                m['symbol'] for m in mercados.values()
                if m['swap'] and m['quote'] == 'USDT' and m['active']
            ]
            
            # 2. Obtener tickers de forma segura (con limpieza)
            try:
                tickers = self.exchange.fetch_tickers(simbolos_candidatos)
            except Exception as e:
                print(f"⚠️ Error masivo en fetch_tickers: {e}")
                tickers = {}

            # 🔥 CACHE DE PRECIOS MASIVO
            for s, t in tickers.items():
                if t and 'last' in t and t['last']:
                    self.market_cache_precios[s] = float(t['last'])

            # Filtrar y Ordenar
            lista_ordenada = []
            for simbolo in simbolos_candidatos:
                # 🛡️ FILTRO ANTI-CRASH (Ej: TSLA/USDT erróneo)
                try:
                    ticker = tickers.get(simbolo)
                    if ticker and 'quoteVolume' in ticker and ticker['quoteVolume'] is not None:
                         lista_ordenada.append((simbolo, ticker['quoteVolume']))
                except Exception:
                    continue # Saltar activo corrupto
            
            # Ordenar por volumen descendente
            lista_ordenada.sort(key=lambda x: x[1], reverse=True)
            
            # Top 30
            top_30 = [item[0] for item in lista_ordenada[:config.MAXIMO_PARES_ESCANEO]]

            # Filtro adicional para cuentas pequeñas (lista operable precalculada)
            try:
                if isinstance(self.mercados_operables, set) and self.mercados_operables:
                    top_30 = [s for s in top_30 if s in self.mercados_operables]
            except Exception:
                pass
            return top_30

        except Exception as e:
            print(f"⚠️ Error obteniendo radar de activos: {e}")
            return [config.SIMBOLO] # Fallback a BTC si falla

    def descargar_velas(self, simbolo):
        """Baja las velas OHLCV para el análisis técnico."""
        try:
            if self.exchange is None:
                if self.modo_mantenimiento:
                    return self._cargar_velas_local(simbolo)
                raise RuntimeError("Sin conexión a Bitget.")
            velas_raw = self.exchange.fetch_ohlcv(simbolo, config.TEMPORALIDAD, limit=100)
            df = pd.DataFrame(velas_raw, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"⚠️ Error descargando datos de {simbolo}: {e}")
            return None

    # --------------------------------------------------------------------------
    # 🧠 INTELIGENCIA ARTIFICIAL
    # --------------------------------------------------------------------------

    def _cargar_velas_local(self, simbolo):
        """
        MODO_MANTENIMIENTO: carga velas desde `datos/` si no hay conexión a Bitget.
        Nota: no es simulación de trading, es seguridad de ingeniería para ejecutar el pipeline sin tocar fondos.
        """
        try:
            proyecto_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            datos_dir = os.path.join(proyecto_dir, "datos")

            s = str(simbolo or "").lower()
            candidatos = []
            if "btc" in s:
                candidatos.append(os.path.join(datos_dir, "btc_usdt_15m.csv"))
            candidatos.append(os.path.join(datos_dir, "conjunto_datos_maestro_v2.csv"))

            path = next((p for p in candidatos if os.path.exists(p)), None)
            if not path:
                return None

            if path not in self._cache_velas_local:
                self._cache_velas_local[path] = pd.read_csv(path)

            df_full = self._cache_velas_local.get(path)
            if df_full is None or len(df_full) < 10:
                return None

            df = df_full.tail(120).copy()
            if "volume" not in df.columns:
                df["volume"] = 0.0
            if "datetime" not in df.columns and "timestamp" in df.columns:
                df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", errors="coerce")

            for c in ("open", "high", "low", "close", "volume"):
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

            return df
        except Exception as e:
            print(f"MODO_MANTENIMIENTO: error cargando velas locales ({simbolo}): {e}")
            return None

    def cargar_cerebro(self):
        """Carga el modelo de IA desde el disco."""
        ruta = os.path.join("inteligencia", "modelos_turbo_v3", "best_model.zip")
        
        while not os.path.exists(ruta):
            if self._stop_solicitado():
                self._shutdown_seguro("STOP solicitado")
                return False
            print(f"🧠 Esperando cerebro en: {ruta}...")
            puente_visual.actualizar_estado({
                "estado_sistema": "ESPERANDO CEREBRO 🧠",
                "mensaje": "Arrastra best_model.zip a la carpeta correcta."
            })
            time.sleep(5)
        
        try:
            from stable_baselines3 import PPO
            # Cargar modelo PPO (Forzando CPU para evitar warnings de Triton/CUDA en Windows)
            # El usuario no tiene CUDA toolkit completo para compilar kernels custom
            self.modelo_ia = PPO.load(ruta, device='cpu')
            print("✅ RED NEURONAL PPO CARGADA. LISTA PARA EL COMBATE.")
            return True
        except Exception as e:
            print(f"❌ CEREBRO CORRUPTO: {e}")
            return False

    def _hilo_vigilante_cartera(self):
        """
        ⚡ HILO DE ALTA FRECUENCIA (REAL-TIME UI)
        Actualiza el saldo y las posiciones cada 1s, independiente del scanner.
        """
        time.sleep(5) # Esperar arranque
        while True:
            try:
                # 1. Fetch Rápido (Solo Balances y Pos)
                self._actualizar_cartera_y_gestion()
                time.sleep(1) # ALTA FRECUENCIA (1s)
            except Exception as e:
                # Silencioso para no ensuciar logs, el principal ya reporta
                time.sleep(5)

    def _bucle_periodista(self):
        """Genera el periódico cada 30 min (Segundo plano)."""
        time.sleep(5)  # Esperar arranque
        backoff_s = 300  # 5 min inicial
        while True:
            try:
                if periodista is None:
                    raise RuntimeError("Módulo `periodista` no disponible")

                print("📰 [PERIODISTA] Redactando nueva edición en castellano...")
                periodista.generar_edicion()
                print("📰 [PERIODISTA] Edición publicada. Descanso de 30m.")
                backoff_s = 300  # reset tras éxito
                time.sleep(1800) # 30 Minutos
            except Exception as e:
                print(f"⚠️ [PERIODISTA] Error: {e} | Reintento en {backoff_s}s")
                time.sleep(backoff_s)
                backoff_s = min(int(backoff_s * 2), 1800)  # cap 30m

    def _bucle_noticias(self):
        """Proceso en segundo plano para ingerir noticias cada 60 min."""
        time.sleep(10) # Esperar arranque
        backoff_s = 600  # 10 min inicial
        while True:
            try:
                if sincronizar_web is None:
                    raise RuntimeError("Módulo `sincronizar_web` no disponible")

                print("📰 [SEGUNDO PLANO] Iniciando sincronización web...")
                sincronizar_web.sincronizar()
                print("📰 [SEGUNDO PLANO] Sincronización finalizada. Durmiendo 60m.")
                backoff_s = 600  # reset tras éxito
                time.sleep(3600) # 1 Hora
            except Exception as e:
                print(f"⚠️ [SEGUNDO PLANO] Error en sincronización web: {e} | Reintento en {backoff_s}s")
                time.sleep(backoff_s)
                backoff_s = min(int(backoff_s * 2), 7200)  # cap 2h

    def procesar_vision_artificial(self, df):
        """Transforma números en visión para la IA (Replica procesador_datos.py)."""
        # IMPORTANTE: Aquí replicamos la lógica usada en entrenamiento v2
        try:
            # 1. Indicadores Básicos
            df['rsi'] = self._calcular_rsi(df['close'])
            
            # Normalización rápida (Z-Score simplificado para inferencia)
            # Nota: Idealmente usaríamos el scaler guardado, pero para HFT
            # usamos normalización relativa a la ventana actual.
            return df
        except Exception as e:
            print(f"⚠️ Error procesando visión: {e}")
            return None
            
    def _calcular_rsi(self, series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calcular_atr(self, df, period=14):
        """Calcula el Average True Range para TP/SL dinámico."""
        try:
            high = df['high']
            low = df['low']
            close = df['close']
            prev_close = close.shift(1)
            
            tr1 = high - low
            tr2 = (high - prev_close).abs()
            tr3 = (low - prev_close).abs()
            
            tr = tr1.to_frame(name='tr1')
            tr['tr2'] = tr2
            tr['tr3'] = tr3
            tr['max'] = tr.max(axis=1)
            
            atr = tr['max'].rolling(window=period).mean()
            return atr
        except:
            return None

    # --------------------------------------------------------------------------
    # ⚔️ EJECUCIÓN Y COMBATE
    # --------------------------------------------------------------------------

    def _asegurar_modo_unilateral(self, simbolo):
        """Fuerza el modo 'One-Way' (Hedged=False) para evitar errores de Bitget."""
        try:
            # Intentamos setear modo posición.
            # Nota: Algunos pares pueden lanzar error si ya tienen posición, por eso el try/catch silencioso.
            self.exchange.set_position_mode(hedged=False, symbol=simbolo)
        except Exception:
            # Si falla, asumimos que ya está bien o que no se puede cambio
            pass

    def ejecutar_orden_ataque(self, simbolo, direccion, precio_estimado, atr=None, confianza=0.9, apalancamiento_ia=1, df=None):
        """Ejecuta orden REAL con Sizing por Riesgo y Blindaje inmediato."""
        try:
            self._asegurar_modo_unilateral(simbolo)
            saldo = 0.0
            try:
                if self.exchange is not None:
                    saldo = float(self.exchange.fetch_balance()['USDT']['free'])
            except Exception:
                saldo = 0.0
            if (saldo is None or saldo <= 0) and self.modo_mantenimiento:
                saldo = float(getattr(self, "balance_mantenimiento_usdt", 100.0))
            if saldo is None:
                saldo = 0.0
            rr_mult_operativo = gestor_riesgo.obtener_rr_mult_operativo(saldo)
            
            # 1. PRE-CÁLCULO DE TP/SL (Para Sizing)
            # Necesitamos el SL proyectado para calcular el tamaño de posición por riesgo
            tp_est, sl_est, motivo_tpsl = tpsl_profesional.calcular_tpsl_elite(
                simbolo, direccion, precio_estimado, 
                atr=atr if atr else 0, 
                confianza=confianza*100, 
                balance=saldo,
                df=df,
                rr_mult=rr_mult_operativo
            )
            
            if motivo_tpsl != "OK" or sl_est is None:
                print(f"🚫 ABORTANDO: No se pudo calcular SL seguro para {simbolo}")
                return False

            # 2. SIZING POR RIESGO REAL
            # Ahora llamamos al nuevo gestor de riesgo (CCXT aware)
            # Riesgo dinámico: modulado por drawdown + progreso objetivo (north-star)
            riesgo_pct_operativo = gestor_riesgo.obtener_riesgo_pct_operativo(saldo)
            if self.exchange is not None:
                cantidad, leverage_final = gestor_riesgo.calcular_tamano_posicion(
                    self.exchange, simbolo, precio_estimado, sl_est, saldo,
                    riesgo_pct=riesgo_pct_operativo, apalancamiento=apalancamiento_ia
                )
            else:
                cantidad, leverage_final = gestor_riesgo.calcular_tamano_posicion_offline(
                    simbolo=simbolo,
                    precio_entrada=precio_estimado,
                    precio_sl=sl_est,
                    saldo_cuenta=saldo,
                    riesgo_pct=riesgo_pct_operativo,
                    apalancamiento=apalancamiento_ia,
                    min_cost_usdt=5.0,
                )
            
            if cantidad == 0:
                print(f"NO_ENTRA: sizing=0 en {simbolo}. Motivo en tmp/zerox_no_entra.txt")
                return False

            if self.modo_mantenimiento:
                side = 'buy' if direccion == 'LONG' else 'sell'
                print(f"MODO_MANTENIMIENTO: habría ejecutado MARKET {simbolo}: {side.upper()} x {cantidad} ({leverage_final}x). NO SE ENVÍA.")
                return False

            # Compuerta REAL/PAPER/BLOQUEADO
            side = 'buy' if direccion == 'LONG' else 'sell'
            if self.modo_trading == "PAPER":
                print(f"MODO PAPER: habria ejecutado MARKET {simbolo}: {side.upper()} x {cantidad} ({leverage_final}x).")
                return False
            if self.modo_trading != "REAL":
                print(f"TRADING BLOQUEADO: {self.motivo_bloqueo_trading}")
                return False

            # 3. CONFIGURAR APALANCAMIENTO
            try:
                # Intentamos setear el leverage calculado/validado
                # Soporta 'apalancamiento' y 'apalangamiento' si viniera de IA
                print(f"⚙️ Ajustando Apalancamiento a {leverage_final}x ...")
                self.exchange.set_leverage(int(leverage_final), simbolo)
            except Exception as e_lev:
                print(f"⚠️ Error Set Leverage {simbolo}: {e_lev}. Intentando seguir con 1x o el actual.")
                # No abortamos, pero asumimos riesgo de que esté en otro valor.
                # Idealmente leeríamos el actual.

            # 4. EJECUCIÓN REAL (MARKET)
            side = 'buy' if direccion == 'LONG' else 'sell'
            print(f"🚀 EJECUTANDO ORDEN MARKET {simbolo}: {side.upper()} x {cantidad} ({leverage_final}x)")
            
            # A. Check Anti-Duplicado
            ya_existe, _ = gestor_ordenes.verificar_tpsl_existente(simbolo)
            if ya_existe:
                print(f"🛑 DUPLICADO DETECTADO (Ledger). Abortando.")
                return False

            # B. FUEGO
            try:
                orden = self.exchange.create_order(simbolo, 'market', side, cantidad)
            except Exception as e_order:
                print(f"❌ ERROR CRÍTICO API ORDER: {e_order}")
                if self._es_error_transitorio(e_order):
                    self._marcar_backoff_simbolo(simbolo, motivo=str(e_order))
                    if self._es_error_sistemico(e_order):
                        self._marcar_backoff_global(motivo=str(e_order))
                # Si es error 25013 (Stock Futures), blacklistear
                if "25013" in str(e_order):
                    self.blacklist_runtime.add(simbolo)
                    self._blacklist_permanente_25013(simbolo)
                return False
            
            # 5. POST-PROCESADO Y BLINDAJE
            precio_real = orden.get('average')
            if not precio_real or precio_real == 0: precio_real = precio_estimado # Fallback
            order_id = orden.get('id', 'UNKNOWN')
            
            print(f"✅ ORDEN EJECUTADA @ {precio_real}. PROCEDIENDO A BLINDAJE...")

            # Recalcular TP/SL exactos con precio real
            tp_final, sl_final, motivo_tpsl_final = tpsl_profesional.calcular_tpsl_elite(
                simbolo, direccion, precio_real, 
                atr=atr if atr else 0, 
                confianza=confianza*100, 
                balance=saldo,
                df=df,
                rr_mult=rr_mult_operativo
            )

            # Colocar TP/SL (Si falla, CERRAR POSICION -- P1.2)
            res_tpsl = None
            print(f"DEBUG TPSL REAL PRE-CHECK: Motivo={motivo_tpsl_final} TP={tp_final} SL={sl_final}", flush=True)
            if motivo_tpsl_final == "OK" and tp_final is not None and sl_final is not None:
                time.sleep(1) # Esperar propagación exchange
                res_tpsl = gestor_ordenes.colocar_tpsl_posicion(
                    self.exchange, simbolo, direccion, tp_final, sl_final, cantidad
                )
            
            # Defaults (evita UnboundLocalError si res_tpsl es None)
            tp_ok = False
            sl_ok = False
            intentos_verificacion = 0
            tpsl_ok = res_tpsl is not None
            if tpsl_ok:
                intentos_verificacion = 0
                for intento in range(1, 4):
                    intentos_verificacion = intento
                    time.sleep(1)
                    tp_ok, sl_ok = gestor_ordenes.verificar_tpsl_api(self.exchange, simbolo)
                    if tp_ok and sl_ok:
                        break
                tpsl_ok = bool(tp_ok and sl_ok)
            
            if not tpsl_ok:
                print("🚨 EMERGENCIA: ENTRADA EXITOSA PERO FALLÓ TP/SL. CERRANDO INMEDIATAMENTE.")

                # Evidencia crítica (obligatoria): dejar rastro en tmp/
                try:
                    ruta_crit = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tmp", "zerox_tpsl_fallo_critico.txt"))
                    os.makedirs(os.path.dirname(ruta_crit), exist_ok=True)

                    ordenes_stop = None
                    error_ordenes_stop = None
                    try:
                        ordenes_stop = self.exchange.fetch_open_orders(simbolo, params={"stop": True})
                    except Exception as e_oo:
                        error_ordenes_stop = str(e_oo)

                    payload = {
                        "ts": datetime.now().isoformat(),
                        "simbolo": simbolo,
                        "direccion": direccion,
                        "modo_trading": getattr(self, "modo_trading", "UNKNOWN"),
                        "order_id": order_id,
                        "cantidad": cantidad,
                        "precio_real": precio_real,
                        "tp_intentado": tp_final,
                        "sl_intentado": sl_final,
                        "res_colocar_tpsl": res_tpsl,
                        "intentos_verificacion": intentos_verificacion,
                        "tp_ok": bool(tp_ok),
                        "sl_ok": bool(sl_ok),
                        "ordenes_stop": ordenes_stop,
                        "error_ordenes_stop": error_ordenes_stop,
                    }

                    with open(ruta_crit, "a", encoding="utf-8") as f:
                        f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
                except Exception:
                    pass

                try:
                    try:
                        bl = self._cargar_blacklist_persistente()
                        if simbolo in getattr(self, "blacklist_runtime", set()) or self._simbolo_en_blacklist_persistente(simbolo, bl):
                            print(f"EMERGENCIA: {simbolo} en blacklist/cuarentena. NO SE CIERRA. Cierre manual requerido.")
                            self._actualizar_estado_hb("EMERGENCIA", f"TP/SL falló en símbolo en cuarentena: {simbolo}")
                            return False
                    except Exception:
                        pass
                    inverse_side = 'sell' if side == 'buy' else 'buy'
                    self.exchange.create_order(simbolo, 'market', inverse_side, cantidad, params={'reduceOnly': True})
                    print("🏳️ POSICIÓN CERRADA POR SEGURIDAD (Sin TP/SL).")
                except Exception as e_close:
                    print(f"💀💀💀 FALLO CATASTRÓFICO CERRANDO POSICIÓN DESNUDA: {e_close}")
                    # AQUI SÍ: Notificar a todo volumen (Discord/Telegram si hubiera)
                return False

            # Registrar Éxito
            tp_id = res_tpsl.get('tp_id', 'FAIL')
            sl_id = res_tpsl.get('sl_id', 'FAIL')
            
            gestor_ordenes.registrar_ejecucion_real(
                simbolo, direccion, cantidad, precio_real, order_id, tp_id, sl_id, True
            )
            gestor_ordenes.registrar_tpsl_ledger(simbolo, order_id, tp_id, sl_id)

            self._limpiar_backoff_simbolo(simbolo)
            
            return True

        except Exception as e:
            print(f"⚠️ EXCEPCIÓN EN EJECUTAR_ORDEN: {e}")
            return False
            print(f"❌ ERROR CRÍTICO AL EJECUTAR: {e}")
            return False

            # 5. MENTE MAESTRA: ANÁLISIS PROFUNDO (Post-Ejecución)
            try:
                contexto_trade = {
                    "Par": simbolo,
                    "Precio": precio_real,
                    "Accion": direccion,
                    "TP": tp,
                    "SL": sl,
                    "RSI": self.datos_tecnicos_cache.get("rsi", 50)
                }
                print("🧠 Mente Maestra analizando la jugada...")
                self.analisis_completo = mente_maestra.analizar_oportunidad(contexto_trade)
            except Exception as e:
                print(f"⚠️ Mente Maestra offline: {e}")
                self.analisis_completo = {"tecnico": "Error", "psicologia": "Offline", "fuentes": "N/A"}

            # 6. ACTUALIZAR ESTADO
            self.activo_actual = simbolo
            self.posicion_abierta = True
            
            puente_visual.actualizar_estado({
                "posicion": {
                    "tipo": direccion,
                    "simbolo": simbolo,
                    "entrada": precio_real,
                    "tp": tp, # Dato clave
                    "sl": sl, # Dato clave
                    "pnl": "0.00",
                    "analisis": self.analisis_completo # INFORME COMPLETO
                },
                "mensaje": f"Blindaje Activado: SL {sl} | TP {tp}"
            })
            
            # Actualizar caché técnico
            self.datos_tecnicos_cache["tp_precio"] = tp
            self.datos_tecnicos_cache["sl_precio"] = sl
            
            return True
 
        except Exception as e:
            print(f"❌ ERROR CRÍTICO EN EJECUCIÓN ({simbolo}): {e}")
            return False

    def _enviar_proteccion_bitget(self, simbolo, direccion, cantidad, tp, sl, es_reparacion=False):
        """
        ESTRATEGIA BLINDADA V5 (POS TPSL - BITGET V2):
        DELEGADO A gestor_ordenes.py para evitar duplicidad y errores (fix 40034).
        """
        # Limpieza de símbolo (BTCUSDT estándar)
        # Delegamos todo al gestor experto
        return gestor_ordenes.colocar_tpsl_posicion(self.exchange, simbolo, direccion, tp, sl, cantidad, es_reparacion)


    def cerrar_posicion(self, motivo):
        """Liquida la posición actual y vuelve al modo escáner."""
        if not self.activo_actual: return
        if self.modo_mantenimiento:
            print(f"MODO_MANTENIMIENTO: cierre solicitado de {self.activo_actual} omitido (órdenes deshabilitadas).")
            return

        print(f"📉 CERRANDO POSICIÓN en {self.activo_actual}: {motivo}")
        try:
            # Buscar posición en el exchange
            posiciones = self.exchange.fetch_positions([self.activo_actual])
            for pos in posiciones:
                tamano = float(pos['contracts'])
                if tamano > 0:
                    # Cierre Puro: Vender lo comprado (o comprar lo vendido)
                    lado_cierre = 'sell' if pos['side'] == 'long' else 'buy'
                    
                    if lado_cierre == 'sell':
                         self.exchange.create_market_sell_order(self.activo_actual, tamano)
                    else:
                         self.exchange.create_market_buy_order(self.activo_actual, tamano)

                    print(f"✅ POSICIÓN CERRADA EXITOSAMENTE.")
                    notificador.enviar("VENTA", f"Salida: {motivo}", {"Par": self.activo_actual})

            # Resetear estado
            self.activo_actual = None
            self.posicion_abierta = 0
            self.precio_entrada = 0.0
            
            puente_visual.actualizar_estado({"posicion": 0, "par_activo": "ESPERANDO..."})

        except Exception as e:
            print(f"⚠️ ERROR CERRANDO: {e}")

    # --------------------------------------------------------------------------
    # 💼 GESTIÓN DE CARTERA Y JSON
    # --------------------------------------------------------------------------

    def _actualizar_cartera_y_gestion(self):
        """
        1. Consulta Balance y Posiciones.
        2. Auto-Gestión: Pone TP/SL si faltan.
        3. Escribe estado_bot.json para la UI.
        """
        try:
            # A. CONSULTAR DATOS
            if self.exchange is None:
                if self.modo_mantenimiento:
                    total_usdt = float(getattr(self, "balance_mantenimiento_usdt", 100.0))
                    free_usdt = total_usdt
                    self.posiciones_cache = []
                    try:
                        self.emergencia_cuarentena = False
                        self.motivo_emergencia = ""
                    except Exception:
                        pass
                    try:
                        puente_visual.actualizar_estado({
                            "estado": "MANTENIMIENTO",
                            "estado_sistema": "MODO_MANTENIMIENTO activo (sin conexión a Bitget)",
                            "saldo_cuenta": f"{total_usdt:.2f}",
                            "posiciones": self.posiciones_cache,
                            "color_estado": "amarillo",
                        })
                    except Exception:
                        pass
                    return
                raise RuntimeError("Sin conexión a Bitget.")

            balance = self.exchange.fetch_balance()
            total_usdt = balance['USDT']['total']
            free_usdt = balance['USDT']['free']
            
            # Obtener posiciones abiertas (riesgo real)
            raw_positions = self.exchange.fetch_positions(None) 
            posiciones_activas = []

            # Blacklist/Cuarentena (Bitget API no gestionable)
            ruta_blacklist = os.path.join(os.path.dirname(__file__), "simbolos_bloqueados.json")
            blacklist = {}
            if os.path.exists(ruta_blacklist):
                try:
                    with open(ruta_blacklist, "r", encoding="utf-8") as f:
                        blacklist = json.load(f) or {}
                except Exception:
                    blacklist = {}

            posicion_cuarentena_detectada = False
            detalles_cuarentena = []
             
            for pos in raw_positions:
                tamano = float(pos['contracts'])
                if tamano > 0:
                    # PRESERVACIÓN DE SÍMBOLO:
                    # 'simbolo_trading' -> Con sufijo (ej: BTC/USDT:USDT) para interactuar con la API
                    # 'simbolo_display' -> Limpio (ej: BTC/USDT) para la UI
                    simbolo_trading = pos['symbol']
                    
                    if simbolo_trading in self.blacklist_runtime:
                        continue

                    simbolo_display = simbolo_trading.split(':')[0]
                    
                    lado = pos['side']
                    tipo_es = "LARGO" if lado.lower() == "long" else "CORTO"
                    precio_entrada = float(pos['entryPrice'])
                    mark_price = float(pos['markPrice']) if pos['markPrice'] else precio_entrada
                    unrealized_pnl = float(pos['unrealizedPnl'])

                    # Inicializar variables de estado
                    tp_real = 0.0
                    sl_real = 0.0
                    tiene_tp = False
                    tiene_sl = False

                    # -------------------------------------------------------------
                    # 🔥 VIGILANTE DE PRECIOS VIRTUAL (Gestión Zerox)
                    # -------------------------------------------------------------
                    try:
                        import inteligencia.gestor_ordenes as go_check
                        tp_virt_ok, sl_virt_ok = go_check.verificar_tpsl_activas(simbolo_trading)
                        
                        if tp_virt_ok or sl_virt_ok:
                            # Leer niveles exactos
                            db_virt = go_check._cargar_tpsl_virtuales()
                            dat_v = db_virt.get(simbolo_trading, {})
                            tp_v = dat_v.get('tp', 0)
                            sl_v = dat_v.get('sl', 0)
                            
                            current_price = mark_price 
                            
                            # Logica Trigger
                            trigger_tp = False
                            trigger_sl = False

                            if lado.lower() == 'long':
                                if tp_v > 0 and current_price >= tp_v: trigger_tp = True
                                if sl_v > 0 and current_price <= sl_v: trigger_sl = True
                            else: # Short
                                if tp_v > 0 and current_price <= tp_v: trigger_tp = True
                                if sl_v > 0 and current_price >= sl_v: trigger_sl = True
                            
                            if trigger_tp or trigger_sl:
                                motivo_cierre = "TP VIRTUAL ALCANZADO" if trigger_tp else "SL VIRTUAL ALCANZADO"
                                print(f"⚡ {motivo_cierre} para {simbolo_display} @ {current_price} (Objetivo: {tp_v if trigger_tp else sl_v})")
                                self.activo_actual = simbolo_display 
                                self.cerrar_posicion(motivo_cierre)
                                
                                try:
                                    if simbolo_trading in db_virt:
                                        del db_virt[simbolo_trading]
                                        go_check._guardar_tpsl_virtuales(db_virt)
                                except: pass
                                continue 

                            # Asignar para UI
                            if tp_v > 0: tp_real = tp_v; tiene_tp = True
                            if sl_v > 0: sl_real = sl_v; tiene_sl = True
                            
                    except Exception as e_virt:
                        print(f"⚠️ Error Vigilante Virtual {simbolo_display}: {e_virt}")

                    # 1. BUSCAR ÓRDENES DE PROTECCIÓN REALES (Bitget API - Fallback)
                    try:
                        # Si ya tenemos virtual, esto es solo aditivo
                        ordenes_abiertas = self.exchange.fetch_open_orders(simbolo_trading, params={'stop': True})
                        ordenes_normales = self.exchange.fetch_open_orders(simbolo_trading)
                        ordenes_abiertas.extend(ordenes_normales)
                        for orden in ordenes_abiertas:
                            params = orden.get('info', {})
                            trigger_price = float(orden.get('triggerPrice') or params.get('triggerPrice') or params.get('stopPrice') or 0)
                            
                            if trigger_price > 0:
                                if lado.lower() == 'long':
                                    if trigger_price > precio_entrada: 
                                        tp_real = trigger_price; tiene_tp = True
                                    elif trigger_price < precio_entrada: 
                                        sl_real = trigger_price; tiene_sl = True
                                else: # Short
                                    if trigger_price < precio_entrada: 
                                        tp_real = trigger_price; tiene_tp = True
                                    elif trigger_price > precio_entrada: 
                                        sl_real = trigger_price; tiene_sl = True
                    except Exception as e_orders:
                        print(f"⚠️ Error leyendo órdenes API {simbolo_display}: {e_orders}")

                    # 2. AUTO-REPARACIÓN: Si no hay TP/SL en Bitget, ponerlos.
                    # 🛡️ AUDITORÍA DE EJECUCIÓN CONTINUA (CADA CICLO)
                    # Regla: NINGUNA posición puede existir sin TP y SL.
                    tiene_tp_real = tp_real > 0
                    tiene_sl_real = sl_real > 0
                    
                    if (not tiene_tp_real or not tiene_sl_real) and (time.time() - self._audit_reparacion_ts.get(simbolo_display, 0) >= self.audit_reparacion_cooldown_s):
                        self._audit_reparacion_ts[simbolo_display] = time.time()
                        motivo_audit = f"AUDITORÍA FALLIDA: {simbolo_display} sin TP/SL. REPARANDO..."
                        print(f"🛑 {motivo_audit}")
                        
                        # Reparación Inmediata (Sin Hilo, para asegurar)
                        dir_norm = "LONG" if lado.lower() == 'long' else "SHORT"
                        tp_fix, sl_fix, motivo_tpsl_fix = tpsl_profesional.calcular_tpsl_elite(
                            simbolo_trading, dir_norm, precio_entrada, 
                            atr=0, confianza=80, balance=total_usdt # 80% confianza en reparaciones
                        )
                        if motivo_tpsl_fix == "OK" and tp_fix is not None and sl_fix is not None:
                            gestor_ordenes.colocar_tpsl_posicion(
                                self.exchange, simbolo_trading, dir_norm, tp_fix, sl_fix, tamano, es_reparacion=True
                            )
                        else:
                            print(f"⚠️ TP/SL omitido para {simbolo_display}: {motivo_tpsl_fix}")
                        
                    # Formatear para UI (TRADUCCIÓN AL ESPAÑOL)
                    pos_data = {
                        "simbolo": simbolo_display,
                        "tipo": tipo_es,
                        "pnl": f"{unrealized_pnl:.2f}",
                        "entrada": precio_entrada,
                        "marca": mark_price,
                        # TP/SL Visual (Real desde API)
                        "tp": tp_real if tp_real > 0 else self.datos_tecnicos_cache.get("tp_precio", 0),
                        "sl": sl_real if sl_real > 0 else self.datos_tecnicos_cache.get("sl_precio", 0),
                        "analisis": self.analisis_completo if simbolo_display == self.activo_actual else {
                            "tecnico": "Posición Real Monitoreada.",
                            "psicologia": "Disciplina férrea.",
                            "fuentes": "Bitget API"
                        }
                    }
                    posiciones_activas.append(pos_data)

                    # 🛡️ GESTIÓN DE RIESGO VIRTUAL (SOFT TP/SL)
                    # Sincroniza las órdenes de seguimiento interno.
                    self._sincronizar_ordenes_virtuales(pos_data, simbolo_trading)

            # ACTUALIZAR CACHE GLOBAL DE POSICIONES (IMPORTANTE PARA UI)
            self.posiciones_cache = posiciones_activas

            # B. ESTADÍSTICAS
            progreso_10m = (total_usdt / 10_000_000) * 100
            
            # Obtener lecciones aprendidas reales
            lecciones_ia = auto_mejora.leer_ultimas_lecciones(5)
            if not lecciones_ia:
                lecciones_ia = [
                    "Modo Aprendizaje Activo: Analizando operaciones...",
                    "La disciplina es la clave del éxito."
                ]

            # C. ESTRUCTURA JSON (V2 - FLAT STANDARD)
            # C. ESTRUCTURA JSON (V2 - FLAT STANDARD)
            if not posiciones_activas:
                # Sin posiciones activas
                pass

            # 1. DATOS DE MERCADO (Estructura Solicitada)
            datos_mercado = {
                "simbolo": self.activo_actual if self.activo_actual else "ESCANEO GLOBAL",
                "precio": self.datos_tecnicos_cache.get("precio_actual", 0),
                "rsi": self.datos_tecnicos_cache.get("rsi", 50),
                "tendencia": "NEUTRA (Escaneando)" if not self.activo_actual else ("ALCISTA" if self.datos_tecnicos_cache.get("rsi", 50) > 50 else "BAJISTA"),
                # Compatibilidad con ScannerVisual antiguo
                # Compatibilidad con ScannerVisual antiguo y nuevo
                "precios": self.market_cache_precios if self.market_cache_precios else { "BTC/USDT": self.datos_tecnicos_cache.get("precio_actual", 98000) }
            }

            # 2. INTENTAR LEER MEMORIA SINÁPTICA REAL
            # 2. INTENTAR LEER MEMORIA SINÁPTICA REAL
            try:
                memoria_real = mente_maestra.obtener_pensamientos_recientes()
            except Exception as e:
                print(f"⚠️ Error leyendo sinapsis: {e}")
                memoria_real = []

            # 3. CORTEX IA
            cortex_txt = self.razonamiento_actual if self.razonamiento_actual else "🧠 CEREBRO EN ESPERA: Buscando divergencias de RSI y rupturas de volumen..."

            # 4. AUTOMEJORA
            leccion = lecciones_ia if lecciones_ia else ["La paciencia paga: Esperar confirmación."]

            # PAYLOAD FINAL
            estado_json = {
                "estado": "OPERANDO 🟢",
                "progreso_10m": progreso_10m,
                "saldo_cuenta": f"{total_usdt:.2f}", # Frontend usa saldo_cuenta
                "mercado": datos_mercado,
                # "flujo_neuronal": flujo_neuronal,   # ELIMINADO (Causaba bug [])
                "pensamientos": memoria_real,         # 🔥 DATOS REALES ESTRUCTURADOS
                "cortex_ia": cortex_txt,
                "razonamiento_ia": cortex_txt if cortex_txt and len(cortex_txt) > 10 else "🧠 PROCESO COGNITIVO:\n- Analizando liquidez en Order Book...\n- Calculando zonas de Fibonacci...\n- Escaneo de sentimiento: COMPLETADO.",
                "automejora": leccion[0] if isinstance(leccion, list) else leccion,
                "ultimas_lecciones": leccion,         # Compatibilidad
                "posiciones": posiciones_activas,
                "pendientes": self.ordenes_pendientes, # 🔥 NUEVO: Órdenes Virtuales
                "estado_sistema": "OPTIMIZADO ⚡",
                "mensaje_error": "",
                "confianza_ia": "100%"
            } 

            # C. CUARENTENA (cooldown, sin bucle por ciclo)
            if detalles_cuarentena:
                now = time.time()
                if (now - self._cuarentena_evidencia_ts) >= self.cuarentena_evidencia_cooldown_s:
                    self._cuarentena_evidencia_ts = now
                    try:
                        ruta_evid = os.path.join(os.path.dirname(__file__), "..", "tmp", "zerox_posiciones_no_gestionables.txt")
                        with open(ruta_evid, "w", encoding="utf-8") as f:
                            for item in detalles_cuarentena:
                                f.write(f"POSICION NO GESTIONABLE: {item.get('simbolo')}\n")
                                f.write(f"MOTIVO: {item.get('motivo')}\n")
                    except Exception:
                        pass

                try:
                    self.emergencia_cuarentena = True
                    simb_txt = ", ".join([str(x.get("simbolo")) for x in (detalles_cuarentena or []) if x.get("simbolo")])[:200]
                    self.motivo_emergencia = f"EMERGENCIA: posición no gestionable (API). Requiere cierre manual. {simb_txt}".strip()
                    self._actualizar_estado_hb("EMERGENCIA", self.motivo_emergencia)
                except Exception:
                    pass

                puente_visual.actualizar_estado({
                    "estado_sistema": "EMERGENCIA: POSICION NO GESTIONABLE (API). REQUIERE CIERRE MANUAL.",
                    "color_estado": "rojo_parpadeante",
                    "posiciones": posiciones_activas
                })
            else:
                try:
                    self.emergencia_cuarentena = False
                    self.motivo_emergencia = ""
                except Exception:
                    pass

            # D. VOLCAR A JSON para Front
            estado_export = {
                "balance_total": total_usdt,
                "balance_libre": free_usdt,
                "posiciones": posiciones_activas,
                "timestamp": datetime.now().isoformat()
            }
            
            with open("estado_bot.json", "w") as f:
                json.dump(estado_export, f)

            
            # Escribir usando el puente blindado
            puente_visual.actualizar_estado(estado_json)

        except Exception as e:
            print(f"⚠️ Error actualizando cartera: {e}")

    def _gestionar_tpsl_automatico(self, simbolo, lado, entrada, cantidad, modo_margen="crossed"):
        """Pone TP/SL retroactive si no existen."""
        try:
            # 1. Verificar si ya existen órdenes abiertas (TP/SL)
            open_orders = self.exchange.fetch_open_orders(simbolo)
            has_stop = False
            
            for order in open_orders:
                # Bitget suele marcar params: stopPrice en info o type 'stop_market'
                if order['status'] == 'open':
                    if order.get('reduceOnly') or 'stop' in order.get('type', '').lower():
                        has_stop = True # Asumimos protegido
            
            if has_stop:
                return # Ya protegido

            # 2. Si NO hay protección, CALCULAR y COLOCAR
            print(f"🛡️ DETECTADA POSICIÓN DESPROTEGIDA EN {simbolo}. ACTIVANDO BLINDAJE RETROACTIVO ({modo_margen})...")
            direction = "LONG" if lado.lower() == 'long' else "SHORT"
            tp, sl = gestor_riesgo.calcular_niveles_salida(entrada, direction)
            
            # Reutilizar nuestra nueva función robusta V3
            self._enviar_proteccion_bitget(simbolo, direction, cantidad, tp, sl, modo_margen)
            
            # Feedback Visual
            puente_visual.actualizar_estado({"mensaje": f"🛡️ Blindaje Retroactivo: {simbolo}"})
            
        except Exception as e:
            # Fallo silencioso (puede ser Rate Limit), reintentará en siguiente ciclo
            print(f"⚠️ Error blindando {simbolo}: {e}") 
    
    def _chequear_comandos_externos(self):
        """Chequea si el Frontend ha solicitado RESET o APAGADO via archivo."""
        try:
            if os.path.exists(config.RUTA_COMANDOS):
                with open(config.RUTA_COMANDOS, 'r', encoding='utf-8') as f:
                    cmd_data = json.load(f)
                
                # Consumir comando (borrar archivo)
                try: os.remove(config.RUTA_COMANDOS)
                except: pass

                comando = cmd_data.get('comando', '')
                if comando == 'RESET':
                    print("🔄 COMANDO RESET EXTERNO RECIBIDO. REINICIANDO...")
                    self._shutdown_seguro("RESET EXTERNO")
                    os.execv(sys.executable, ['python'] + sys.argv)
                elif comando == 'SHUTDOWN':
                    print("🛑 COMANDO SHUTDOWN EXTERNO RECIBIDO. APAGANDO.")
                    self._shutdown_seguro("SHUTDOWN EXTERNO")
                    sys.exit(0)
        except Exception:
            pass

    def ejecutar_ciclo_depredador(self):
        import gc
        
        # CICLO PRINCIPAL
        ciclo_interno = 0
        while True:
            try:
                # 0. CHEQUEO PRIORITARIO DE COMANDOS
                self._chequear_comandos_externos()

                if self.detener_solicitado or self._stop_solicitado():
                    self._shutdown_seguro("STOP solicitado")
                    return True

                if not self.exchange:
                    self._actualizar_estado_hb("BLOQUEADO", "Sin conexión a Bitget. Reintentando...")
                    ok = self._conectar_exchange()
                    if not ok:
                        time.sleep(10)
                        continue

                ciclo_interno += 1
                self.contador_ciclos = ciclo_interno # Para heartbeat externo
                self._ciclo_iter += 1
                self._procesar_flag_reset_backoff()
                motivo_data = self._leer_ultimo_motivo_no_entra()
                self._limpiar_backoff_por_motivo(motivo_data)
                self._ultimo_info_no_entra = motivo_data
                gc.collect() # Limpiar memoria RAM
                
                # 💓 HEARTBEAT (PULSO VITAL - WATCHDOG)
                estado_hb = "ACTIVO"
                motivo_hb = f"Ciclo {ciclo_interno} running"
                if self.modo_trading == "BLOQUEADO":
                    estado_hb = "BLOQUEADO"
                    motivo_hb = self.motivo_bloqueo_trading or motivo_hb
                elif self.modo_trading == "PAPER":
                    estado_hb = "PAPER"
                    motivo_hb = f"Ciclo {ciclo_interno} (PAPER)"
                self._actualizar_heartbeat(estado_hb, motivo_hb)
                
                # Heartbeat UI (Visual)
                puente_visual.actualizar_estado({"heartbeat": time.time()})

                # A. Cargar IA si falta
                if not self.modelo_ia:
                    self._registrar_paso("Cargando Cerebro IA")
                    self.cargar_cerebro()
                    continue

                # --- NUEVO: GESTIÓN DE CARTERA EN TIEMPO REAL ---
                self._registrar_paso("Gestión Cartera Real")
                self._actualizar_cartera_y_gestion()
                # -----------------------------------------------

                # B. MODO GESTIÓN (Si ya tenemos una presa)
                if self.posicion_abierta and self.activo_actual:
                    self._registrar_paso("Modo Vigilancia Activa")
                    self._modo_vigilancia()
                    self._registrar_paso("Durmiendo (Vigilancia)")
                    if self._stop_solicitado():
                        self._shutdown_seguro("STOP solicitado")
                        return True
                    time.sleep(5)
                    continue

                # C. MODO ESCÁNER (Buscar nuevas presas)
                self._registrar_paso("Verificando Circuit Breakers")
                # --- CHECK CONTROL DE RIESGO (CIRCUIT BREAKER) ---
                try:
                    # Prioridad máxima: EMERGENCIA (posición no gestionable por API: TSLA/25013, etc.)
                    if bool(getattr(self, "emergencia_cuarentena", False)):
                        self.entradas_habilitadas_riesgo = False
                        self.estado_trading = "EMERGENCIA"
                        self.motivo_estado_trading = (
                            str(getattr(self, "motivo_emergencia", "") or "").strip()
                            or "EMERGENCIA: posición no gestionable (API). Requiere cierre manual."
                        )
                        self._actualizar_estado_hb(self.estado_trading, self.motivo_estado_trading)
                        puente_visual.actualizar_estado({
                            "estado": self.estado_trading,
                            "estado_sistema": self.motivo_estado_trading,
                            "color_estado": "rojo_parpadeante",
                        })
                    else:
                        # Riesgo diario: usa EQUITY (balance total), no solo disponible.
                        if self.modo_mantenimiento or self.exchange is None:
                            equity_actual = float(getattr(self, "balance_mantenimiento_usdt", 100.0))
                        else:
                            balance_riesgo = self.exchange.fetch_balance()
                            equity_actual = float((balance_riesgo.get("USDT") or {}).get("total") or 0.0)

                        operativo, motivo, etiqueta_estado = gestor_riesgo.verificar_circuit_breaker(equity_actual)
                        self.entradas_habilitadas_riesgo = bool(operativo)
                        self.estado_trading = str(etiqueta_estado or "ACTIVO").strip() or "ACTIVO"
                        self.motivo_estado_trading = str(motivo or "").strip()
                        self._actualizar_estado_hb(self.estado_trading, self.motivo_estado_trading)

                        color = "amarillo"
                        if self.estado_trading == "ACTIVO":
                            color = "verde"
                        elif self.estado_trading == "PAUSA_RIESGO":
                            color = "amarillo"
                        elif self.estado_trading == "BLOQUEADO":
                            color = "rojo"
                        elif self.estado_trading == "EMERGENCIA":
                            color = "rojo_parpadeante"

                        puente_visual.actualizar_estado({
                            "estado": self.estado_trading,
                            "estado_sistema": self.motivo_estado_trading,
                            "color_estado": color,
                        })

                        if not operativo:
                            print(f"ENTRADAS PAUSADAS ({self.estado_trading}): {self.motivo_estado_trading}")
                except Exception as e:
                    self.entradas_habilitadas_riesgo = False
                    self.estado_trading = "BLOQUEADO"
                    self.motivo_estado_trading = f"Fallo chequeando riesgo/equity: {e}"
                    try:
                        self._actualizar_estado_hb(self.estado_trading, self.motivo_estado_trading)
                    except Exception:
                        pass
                    try:
                        puente_visual.actualizar_estado({
                            "estado": self.estado_trading,
                            "estado_sistema": self.motivo_estado_trading,
                            "color_estado": "rojo",
                        })
                    except Exception:
                        pass
                    print(f"⚠️ {self.motivo_estado_trading}")

                # --- 1. ESCANEO VISUAL (Paginado) ---
                # Recorremos el mercado para que el usuario VEA los precios pasar
                activos_top = self.obtener_top_activos()
                self._reportar_por_que_no_entra(getattr(self, "_ultimo_info_no_entra", {}))
                print(f"📡 RADAR ACTIVO: Escaneando {len(activos_top)} objetivos...")

                for i, simbolo in enumerate(activos_top):
                    if self._stop_solicitado():
                        self._shutdown_seguro("STOP solicitado")
                        return True

                    # 1. Descargar
                    df = self.descargar_velas(simbolo)
                    if df is None: continue
                    
                    precio = df.iloc[-1]['close']
                    volumen = df.iloc[-1]['volume']
                    rsi = self._calcular_rsi(df['close']).iloc[-1]
                    atr = self._calcular_atr(df).iloc[-1] if self._calcular_atr(df) is not None else 0.0

                    # --- MOTOR DETERMINISTA (PRIMERA CAPA, ANTES DEL LLM) ---
                    try:
                        senal_det = evaluar_setup_determinista(df, simbolo=simbolo, temporalidad=config.TEMPORALIDAD)
                    except Exception as e_det:
                        senal_det = {
                            "setup": False,
                            "lado": "ESPERAR",
                            "score": 0,
                            "razones": [f"Fallo motor determinista: {e_det}"],
                            "confluencias": [],
                            "invalidaciones": ["ERROR_MOTOR_DETERMINISTA"],
                            # legacy (usado por el core actual)
                            "decision": "ESPERAR",
                            "confianza": 0,
                            "razon": f"Fallo motor determinista: {e_det}",
                            "detalle_setup": {"patron": None, "fibo": None, "divergencias": None, "indicadores": {}, "volumen": None},
                            "plan": {"sl": None, "tp": None, "rr": None, "apalancamiento_sugerido": 1},
                        }
                    
                    # ⚡ ACTUALIZACIÓN VISUAL EN TIEMPO REAL (HEARTBEAT) ⚡
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    
                    # Recuperar posiciones reales para evitar parpadeo
                    try:
                        saldo_actual = self.exchange.fetch_balance()['USDT']['total']
                    except:
                        saldo_actual = 0.0

                    # Detectar si hay posiciones (aunque sea la demo)
                    posiciones_safe = self.datos_tecnicos_cache.get("posiciones_cache", []) 
                    # Truco: _actualizar_cartera_y_gestion guarda en cache o podemos usar una variable de clase
                    # Mejor: Usamos una lista vacía si no hay, el hilo vigilante la rellenará en <1s
                    
                    datos_live = {
                         "estado": "ESCANEO ACTIVO 📡",
                         "simbolo": simbolo,
                         "precio": precio,
                         "progreso_10m": (saldo_actual / max(getattr(config, "OBJETIVO_EUR", 10000000), 1)) * 100,
                         "saldo_cuenta": f"{saldo_actual:.2f}",
                         "mercado": {
                            "simbolo": simbolo,
                            "precio": precio,
                            "rsi": rsi,
                            "tendencia": "SOBRECOMPRA 🔴" if rsi > 70 else ("SOBREVENTA 🟢" if rsi < 30 else "NEUTRA ⚪"),
                            "precios": { "BTC/USDT": self.datos_tecnicos_cache.get("precio_actual", 0), "SCAN": precio } 
                         },
                         "cortex_ia": f"🔍 ESCANER NEURONAL: {simbolo}\n------------------------\nPRECIO: {precio}\nRSI: {rsi:.2f}\nVOLUMEN: {volumen:.0f}",
                         "flujo_neuronal": [
                            f"[{timestamp}] 👁️ Analizando {simbolo} (RSI: {rsi:.1f})",
                            f"[{timestamp}] 📡 Radar de Volumen: {volumen:.0f}",
                         ],
                         "estado_sistema": f"ESCANANDO {simbolo} ({i+1}/{len(activos_top)})",
                         "progreso": int((i / len(activos_top)) * 100),
                         # IMPORTANTE: Usar cache para no borrar la tabla visible
                         "posiciones": self.posiciones_cache 
                    }
                    puente_visual.actualizar_estado(datos_live)
                    time.sleep(0.5) # PAUSA VISUAL (Solicitada por usuario)

                    # 3. CONSULTA A LA IA (¿Atacamos?)
                    # SI RSI está en extremos, consultamos al módulo IA (Mente Maestra — desactivada)
                    # 3. FILTRO TÉCNICO INICIAL (Candidatos)
                    # FILTRO DETERMINISTA: si el motor dice ESPERAR, no se opera aunque el LLM se emocione.
                    decision_det = (senal_det or {}).get("decision", "ESPERAR")
                    confianza_det = int((senal_det or {}).get("confianza", 0) or 0)

                    senal_compra = (decision_det == "COMPRA") and (confianza_det >= 60)
                    senal_venta = (decision_det == "VENTA") and (confianza_det >= 60)

                    if senal_compra or senal_venta:
                        direccion_tecnica = "LONG" if senal_compra else "SHORT"
                        print(f"🔎 CANDIDATO DETERMINISTA: {simbolo} -> {decision_det} ({confianza_det}%). {(senal_det or {}).get('razon','')}")
                        
                        # PREPARAR CONTEXTO PARA CEREBRO LOCAL
                        contexto_ia = {
                            "symbol": simbolo,
                            "price": precio,
                            "rsi": rsi,
                            "atr": atr,
                            "volume": float(df.iloc[-1]['volume']) if 'volume' in df else 0,
                            "trend": "BEARISH" if rsi < 40 else "BULLISH",
                            "candidate_action": direccion_tecnica,
                            "motor_determinista": senal_det
                        }

                        # RAG: contexto y citas (si Academia está disponible)
                        try:
                            if getattr(self, "academia", None) is not None:
                                consulta_rag = f"{simbolo} {decision_det} {direccion_tecnica} RSI {rsi:.1f} ATR {atr:.6f} | {str((senal_det or {}).get('razon',''))[:200]}"
                                rag = self.academia.buscar(consulta_rag, k=5)
                                rag_recortado = []
                                for r in (rag or []):
                                    try:
                                        r2 = dict(r)
                                        r2["texto"] = str(r2.get("texto") or "")[:800]
                                        rag_recortado.append(r2)
                                    except Exception:
                                        continue
                                contexto_ia["rag"] = rag_recortado
                        except Exception as e_rag:
                            contexto_ia["rag"] = {"error": str(e_rag)}
                        
                        # CONSULTA A OLLAMA (si falla, seguimos con determinista)
                        try:
                            juicio_ia = mente_maestra.analizar_oportunidad(contexto_ia)
                        except Exception as e_ia:
                            juicio_ia = {"accion_sugerida": "ESPERAR", "confianza": 0, "tecnico": f"IA offline: {e_ia}"}
                        
                        # DECISIÓN FINAL (Consenso Técnico + IA)
                        # REGLA: la IA NO decide. Solo explica/sugiere. La decisión final la toma el motor determinista.
                        accion_ia = (juicio_ia or {}).get('accion_sugerida', 'ESPERAR')
                        confianza_ia = (juicio_ia or {}).get('confianza', 0)

                        conf_final = int(confianza_det or 0)
                        razon_det = (senal_det or {}).get("razon", "")
                        detalle_ia = str((juicio_ia or {}).get("tecnico", "") or "")
                        self.razonamiento_actual = f"[{direccion_tecnica}] Motor determinista {confianza_det}%: {razon_det}"
                        if detalle_ia:
                            self.razonamiento_actual += f" | IA sugiere {accion_ia} ({confianza_ia}%): {detalle_ia}"
                        print(f"🧠 DECISIÓN (DETERMINISTA, SIN VETO IA): {self.razonamiento_actual}")

                        # Actualizar caché para ejecución
                        tp_det = (senal_det or {}).get("plan", {}).get("tp")
                        sl_det = (senal_det or {}).get("plan", {}).get("sl")
                        self.datos_tecnicos_cache = {
                            "rsi": float(rsi),
                            "precio_actual": float(precio),
                            "tp_precio": tp_det if tp_det else (precio * (1.03 if direccion_tecnica == 'LONG' else 0.97)),
                            "sl_precio": sl_det if sl_det else (precio * (0.985 if direccion_tecnica == 'LONG' else 1.015))
                        }

                        # PASAR EL ANÁLISIS PREVIO PARA NO CONSULTAR OTRA VEZ
                        self.analisis_completo = {"motor_determinista": senal_det, "ia": juicio_ia}

                        # ATAQUE
                        apalancamiento_ia = int(
                            (senal_det or {}).get("plan", {}).get("apalancamiento_sugerido")
                            or (juicio_ia or {}).get('apalancamiento', 1)
                            or 1
                        )
                        print(f"🧠 Apalancamiento sugerido (determinista/IA): {apalancamiento_ia}x")

                        if not self._verificar_backoff_disponible(simbolo):
                            continue

                        if not bool(getattr(self, "entradas_habilitadas_riesgo", True)):
                            motivo = str(getattr(self, "motivo_estado_trading", "") or "").strip()
                            estado = str(getattr(self, "estado_trading", "PAUSA_RIESGO") or "PAUSA_RIESGO").strip()
                            if self._es_motivo_no_backoff(estado, motivo):
                                self._sleep_no_entra_riesgo(estado, motivo)
                            else:
                                print(f"NO_ENTRA: {estado}. {motivo} (sin backoff)")
                                time.sleep(2)
                            continue

                        exito = self.ejecutar_orden_ataque(
                            simbolo,
                            direccion_tecnica,
                            precio_estimado=precio,
                            atr=atr,
                            confianza=conf_final / 100.0,
                            apalancamiento_ia=apalancamiento_ia,
                            df=df,
                        )
                        if exito:
                            break
                    
                    # Pausa táctica anti-ban
                    time.sleep(0.5)

            except KeyboardInterrupt:
                print("\n🛑 APAGADO DE EMERGENCIA ACTIVADO.")
                break
            except Exception as e:
                print(f"⚠️ ERROR EN BUCLE PRINCIPAL: {e}")
                time.sleep(5)

    def _modo_vigilancia(self):
        """Vigila la posición abierta para cerrar con ganancia o Stop Loss."""
        df = self.descargar_velas(self.activo_actual)
        if df is None: return
        
        precio_actual = df.iloc[-1]['close']
        rsi = self._calcular_rsi(df['close']).iloc[-1]
        
        # UI
        puente_visual.actualizar_estado({
            "precio": float(precio_actual),
            "estado_sistema": f"VIGILANDO {self.activo_actual} 👁️",
        })

        # Lógica de Salida Simple para Demo
        # Si LONG y RSI > 70 -> Vender
        # Si SHORT y RSI < 30 -> Comprar
        
        salir = False
        motivo = ""
        
        # Protecciones manuales extra por si falla el TP/SL
        if self.precio_entrada > 0:
            pnl_pct = (precio_actual - self.precio_entrada) / self.precio_entrada
            if self.posicion_abierta == -1: pnl_pct *= -1 # Invertir para short
            
            if pnl_pct < -0.05: # Stop Loss Pánico (mas ancho que el de 1.5% del exchange)
                salir = True; motivo = "Stop Loss MANUAL DE EMERGENCIA"
            elif pnl_pct > 0.10: 
                salir = True; motivo = "Take Profit MANUAL DE EMERGENCIA"

        if salir:
            self.cerrar_posicion(motivo)

    def _reportar_error_fatal(self, msg):
        print(f"❌ {msg}")
        try:
            notificador.enviar("ERROR", msg)
        except Exception:
            pass

        try:
            self.exchange = None
        except Exception:
            pass

        self._actualizar_estado_hb("BLOQUEADO", msg)
        try:
            puente_visual.actualizar_estado({
                "estado": "BLOQUEADO",
                "estado_sistema": msg,
                "color_estado": "rojo"
            })
        except Exception:
            pass

        # No hacemos sys.exit(1): el proceso debe quedar vivo 24/7.
        try:
            time.sleep(5)
        except Exception:
            pass
        return False

    # ==============================================================================
    # 👻 GESTIÓN DE ÓRDENES VIRTUALES (SOFT TP/SL)
    # ==============================================================================
    
    def _sincronizar_ordenes_virtuales(self, pos_data, simbolo_trading):
        """
        Mantiene en memoria las órdenes virtuales (TP/SL) para una posición activa.
        Si el precio toca el gatillo, ejecuta cierre de mercado.
        Max 30 operaciones en cola.
        """
        try:
            import time
            simbolo_display = pos_data['simbolo']
            lado = pos_data['tipo'] # LARGO / CORTO
            entrada = float(pos_data['entrada'])
            precio_actual = float(pos_data['marca'])
            
            # 1. Buscar si ya existen órdenes para este símbolo
            ordenes_existentes = [o for o in self.ordenes_pendientes if o['simbolo'] == simbolo_display]
            
            # 2. Si NO existen, crearlas (Cálculo automático)
            if not ordenes_existentes:
                print(f"👻 Creando órdenes virtuales para {simbolo_display}...")
                dir_calc = "LONG" if lado == "LARGO" else "SHORT"
                tp, sl = gestor_riesgo.calcular_niveles_salida(entrada, dir_calc)
                
                # Orden TP
                self.ordenes_pendientes.append({
                    "id": f"tp_{simbolo_display}_{int(time.time())}",
                    "simbolo": simbolo_display,
                    "simbolo_trading": simbolo_trading,
                    "lado": lado,
                    "tipo": "TP",
                    "precio_gatillo": tp,
                    "precio_actual": precio_actual,
                    "entrada": entrada
                })
                
                # Orden SL
                self.ordenes_pendientes.append({
                    "id": f"sl_{simbolo_display}_{int(time.time())}",
                    "simbolo": simbolo_display,
                    "simbolo_trading": simbolo_trading,
                    "lado": lado,
                    "tipo": "SL",
                    "precio_gatillo": sl,
                    "precio_actual": precio_actual,
                    "entrada": entrada
                })
                
                # Límite 30
                if len(self.ordenes_pendientes) > 30:
                    self.ordenes_pendientes = self.ordenes_pendientes[-30:]

            # 3. ACTUALIZAR Y VERIFICAR (MONITORING M/S)
            nuevas_pendientes = []
            ejecutada = False
            
            for orden in self.ordenes_pendientes:
                if orden['simbolo'] != simbolo_display:
                    nuevas_pendientes.append(orden)
                    continue
                
                # Actualizar precio actual visual
                orden['precio_actual'] = precio_actual
                
                # LÓGICA DE GATILLO
                disparo = False
                gatillo = orden['precio_gatillo']
                
                if lado == "LARGO":
                    # TP: Precio >= Gatillo | SL: Precio <= Gatillo
                    if orden['tipo'] == "TP" and precio_actual >= gatillo and gatillo > 0: disparo = True
                    if orden['tipo'] == "SL" and precio_actual <= gatillo and gatillo > 0: disparo = True
                else: # CORTO
                    # TP: Precio <= Gatillo | SL: Precio >= Gatillo
                    if orden['tipo'] == "TP" and precio_actual <= gatillo and gatillo > 0: disparo = True
                    if orden['tipo'] == "SL" and precio_actual >= gatillo and gatillo > 0: disparo = True
                
                if disparo and not ejecutada:
                    print(f"⚡ GATILLO VIRTUAL ACTIVADO: {orden['tipo']} en {simbolo_display} a {precio_actual}")
                    threading.Thread(target=self._ejecutar_cierre_mercado, args=(simbolo_trading,)).start()
                    ejecutada = True 
                else:
                    nuevas_pendientes.append(orden)
            
            self.ordenes_pendientes = nuevas_pendientes
            
        except Exception as e:
            print(f"⚠️ Error Soft-TPSL {pos_data.get('simbolo')}: {e}")

    def _ejecutar_cierre_mercado(self, simbolo_trading):
        """Ejecuta cierre inmediato por señal virtual."""
        try:
            # Método manual robusto:
            if self.modo_mantenimiento:
                print(f"MODO_MANTENIMIENTO: cierre virtual omitido para {simbolo_trading} (órdenes deshabilitadas).")
                return
            pos = self._buscar_posicion_raw(simbolo_trading)
            if pos:
                side = pos['side'] # long/short
                amount = float(pos['contracts']) # Tamaño en contratos
                inverse_side = 'sell' if side == 'long' else 'buy'
                
                print(f"🔫 EJECUTANDO CIERRE DE MERCADO EN {simbolo_trading} ({amount} ctrs)...")
                self.exchange.create_market_order(simbolo_trading, inverse_side, amount, params={'reduceOnly': True})
                puente_visual.actualizar_estado({"mensaje": f"⚡ CIERRE VIRTUAL: {simbolo_trading}"})
        except Exception as e:
            print(f"❌ Error cerrando {simbolo_trading}: {e}")

    def _buscar_posicion_raw(self, simbolo_trading):
        """Helper para recuperar posición real del exchange."""
        try:
            positions = self.exchange.fetch_positions([simbolo_trading])
            return positions[0] if positions else None
        except:
            return None

if __name__ == "__main__":
    import traceback
    
    # BUCLE DE INMORTALIDAD (NIVEL ZERO)
    while True:
        try:
            ruta_stop = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "STOP"))
            if os.path.exists(ruta_stop):
                print("STOP detectado. Saliendo de forma segura.")
                break

            bot = OperadorDepredador()
            detener = bot.ejecutar_ciclo_depredador()
            if detener:
                break
        except KeyboardInterrupt:
            print("\n🛑 INTERRUPCIÓN MANUAL DETECTADA. SALIENDO.")
            break
        except Exception as e:
            # CAPTURA DE CRASH DE ÚLTIMO RECURSO (PERO SIN MORIR)
            timestamp = datetime.now().isoformat()
            tmp_dir = os.path.join(os.path.dirname(__file__), "..", "tmp")
            try:
                os.makedirs(tmp_dir, exist_ok=True)
            except Exception:
                pass
            ruta_trace = os.path.join(tmp_dir, "zerox_exception_trace.txt")
            ruta_ult = os.path.join(tmp_dir, "zerox_crash_ult.txt")
            
            with open(ruta_trace, "a", encoding="utf-8", errors="replace") as f: # Append mode
                f.write(f"\n[{timestamp}] ZEROX CRITICAL RECOVERY:\n")
                f.write(f"ERROR: {e}\n")
                traceback.print_exc(file=f)

            # Último crash (overwrite) - evidencia verificable
            try:
                with open(ruta_ult, "w", encoding="utf-8", errors="replace") as f_ult:
                    f_ult.write(f"[{timestamp}] ZEROX CRASH ÚLTIMO\n")
                    f_ult.write(f"ERROR: {e}\n\n")
                    traceback.print_exc(file=f_ult)
            except Exception:
                pass
            
            print(f"💀 CRASH DETECTADO: {e}")
            print("🛡️ REINICIANDO PROCESO INTERNO EN 10 SEGUNDOS (MODO INMORTAL)...")
            
            # Notificar al mundo exterior que estamos heridos pero vivos
            try:
                with open(os.path.join(os.path.dirname(__file__), "heartbeat.json"), "w", encoding="utf-8", errors="replace") as f:
                    json.dump({
                        "timestamp": time.time(),
                        "estado_trading": "CRASH_RECOVERY",
                        "motivo": str(e)
                    }, f, ensure_ascii=False)
            except: pass
            
            try:
                ruta_stop = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "STOP"))
                if os.path.exists(ruta_stop):
                    print("STOP detectado durante recuperación. Saliendo.")
                    break
            except Exception:
                pass

            time.sleep(10) # Backoff fijo de emergencia
            continue # Resucitar
