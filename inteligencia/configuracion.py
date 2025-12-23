import os
from dotenv import load_dotenv

# Cargar variables de entorno desde la raíz del proyecto
ruta_env = os.path.join(os.path.dirname(__file__), "../.env")
load_dotenv(ruta_env)

# PARCHE DE ESTABILIDAD - IA y DRIVERS
import warnings
# Permitir descargas sin SSL si hay bloqueos
os.environ["HF_HUB_DISABLE_SSL_VERIFY"] = "1"
# Suprimir advertencias de Triton en Windows (falta de CUDA SDK)
warnings.filterwarnings("ignore", message="Failed to find cuobjdump.exe")
warnings.filterwarnings("ignore", message="Failed to find nvdisasm.exe")
warnings.filterwarnings("ignore", category=UserWarning, module="triton.knobs")

# -----------------------------
# Helpers de entorno (robustos)
# -----------------------------
def _env_flag(nombre: str, default: bool = False) -> bool:
    try:
        raw = (os.getenv(nombre) or "").strip().lower()
    except Exception:
        raw = ""
    if raw == "":
        return bool(default)
    return raw in ("1", "true", "yes", "y", "si", "sí", "on")

# Credenciales Bitget (Futuros)
CLAVE_API = os.getenv("CLAVE_API") or os.getenv("BITGET_API_KEY") or os.getenv("BITGET_KEY")
SECRETO_API = os.getenv("SECRETO_API") or os.getenv("BITGET_SECRET_KEY") or os.getenv("BITGET_SECRET")
CONTRASENA_API = os.getenv("CONTRASENA_API") or os.getenv("BITGET_PASSWORD") or os.getenv("BITGET_PASSPHRASE")

# Configuración del Bot
SIMBOLO = "BTC/USDT:USDT" # Par de Futuros
TEMPORALIDAD = "15m"
APALANCAMIENTO = 5 # Por defecto (el usuario puede cambiarlo en la UI, pero aquí es fijo por ahora)
try:
    APALANCAMIENTO_MAX = int(os.getenv("APALANCAMIENTO_MAX") or APALANCAMIENTO)
except Exception:
    APALANCAMIENTO_MAX = APALANCAMIENTO
STOP_LOSS_PORCENTAJE = 0.05 # 5% de pérdida máxima por operación
MAX_PAIRS_SCAN = 30 # (Legacy)
MAXIMO_PARES_ESCANEO = 30 # Top criptomonedas a analizar

# MODO DE OPERACIÓN
# ¡¡MODO REAL ACTIVADO POR ORDEN DEL USUARIO!!
# Se ignora la variable de entorno para garantizar ejecución LIVE.
TRADING_MODE = "REAL"
MODO_OPERACION = TRADING_MODE

# =========================================================
# MODO MANTENIMIENTO (SEGURIDAD DE INGENIERÍA)
# =========================================================
# - Si `MODO_MANTENIMIENTO=1`: NO se envían órdenes al exchange, pero el pipeline sigue vivo.
MODO_MANTENIMIENTO = False 
try:
    BALANCE_MANTENIMIENTO_USDT = float(os.getenv("BALANCE_MANTENIMIENTO_USDT") or 100.0)
except Exception:
    BALANCE_MANTENIMIENTO_USDT = 100.0


# Rutas de Archivos (Uso de rutas absolutas)
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # .../zerox-core/inteligencia
RUTA_MODELO = os.path.join(BASE_DIR, "modelos_v2_turbo", "best_model.zip")
RUTA_ESTADO = os.path.join(BASE_DIR, "..", "interfaz", "public", "estado_bot.json")
RUTA_COMANDOS = os.path.join(BASE_DIR, "instruccion_bot.json")

# Notificaciones
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# =========================================================
# OBJETIVO INTERNO (NORTH-STAR) — NO ES GARANTÍA
# =========================================================
# Se usa únicamente para modular agresividad (riesgo/rr), no para prometer beneficios.
try:
    OBJETIVO_EUR = int(os.getenv("OBJETIVO_EUR") or 10000000)
except Exception:
    OBJETIVO_EUR = 10000000

MODO_OBJETIVO = "NORTH_STAR"
PERFIL_RIESGO = "AGRESIVO" # ¡MODO AGRESIVO FORZADO! (Cuentas pequeñas: Vía libre)

