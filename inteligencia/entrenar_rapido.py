import os
import time
import pandas as pd
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback

# Importamos el entorno personalizado (asegúrate de que este archivo existe y funciona)
from entorno_trading_v2 import EntornoTradingBitgetV2

# --- CONFIGURACIÓN DE VELOCIDAD EXTREMA ---
N_ENVS = 8              # Número de núcleos de CPU a usar (8 entornos simultáneos)
CONTROLADOR_VEHICULO = SubprocVecEnv # Paralelismo real (multiprocesamiento)
DISPOSITIVO = "cuda"    # Usar GPU NVIDIA (RTX 2070)
PASOS_TOTALES = 1_000_000 # ~10-12 minutos en RTX 2070 (Aprox 1500 FPS)

# Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_DATOS = os.path.join(BASE_DIR, "..", "datos", "conjunto_datos_maestro_v2.csv")
DIR_MODELOS = os.path.join(BASE_DIR, "modelos_turbo_v3")
DIR_LOGS = os.path.join(BASE_DIR, "logs_turbo_v3")

class NotificadorEspañol(BaseCallback):
    """
    Callback avanzado para replicar la tabla de Stable Baselines 3 pero en ESPAÑOL.
    Accede al logger interno para extraer las métricas de entrenamiento.
    """
    def __init__(self, check_freq: int, verbose=1):
        super(NotificadorEspañol, self).__init__(verbose)
        self.check_freq = check_freq
        self.traducciones = {
            # Rollout
            "rollout/ep_len_mean": "Promedio Longitud Ep.",
            "rollout/ep_rew_mean": "Promedio Recompensa",
            # Time
            "time/fps": "FPS (Velocidad)",
            "time/iterations": "Iteraciones",
            "time/time_elapsed": "Tiempo Transcurrido",
            "time/total_timesteps": "Pasos Totales",
            # Train
            "train/approx_kl": "Aprox. KL (Divergencia)",
            "train/clip_fraction": "Fracción Recorte",
            "train/clip_range": "Rango Recorte",
            "train/entropy_loss": "Pérdida Entropía",
            "train/explained_variance": "Varianza Explicada",
            "train/learning_rate": "Tasa Aprendizaje",
            "train/loss": "Pérdida Total",
            "train/n_updates": "Actualizaciones",
            "train/policy_gradient_loss": "Pérdida Gradiente",
            "train/value_loss": "Pérdida Valor",
            "train/std": "Desviación Est."
        }

    def _on_step(self) -> bool:
        return True

    def on_rollout_start(self) -> None:
        """
        Al inicio del rollout es cuando PPO suele haber terminado la iteración anterior 
        y los logs están listos en self.logger.name_to_value.
        """
        # Accedemos a los valores registrados en el logger
        if hasattr(self.logger, 'name_to_value') and self.logger.name_to_value:
            self._imprimir_tabla_espanol(self.logger.name_to_value)

    def _imprimir_tabla_espanol(self, metrics_dict):
        # Filtramos solo las métricas que nos interesan traducir
        tabla = []
        for key, value in metrics_dict.items():
            if key in self.traducciones:
                nombre_es = self.traducciones[key]
                if "learning_rate" in key or "approx_kl" in key:
                    valor_fmt = f"{value:.6f}"
                elif "loss" in key or "mean" in key or "std" in key:
                    valor_fmt = f"{value:.4f}"
                elif "fps" in key or "timesteps" in key or "iterations" in key or "updates" in key:
                    valor_fmt = f"{int(value)}"
                else:
                    valor_fmt = f"{value:.4f}"
                
                tabla.append((nombre_es, valor_fmt))
        
        if not tabla:
            return

        print(f"╔══════════════════════════════════════════════╗")
        print(f"║ 🇪🇸  REPORTE DE ENTRENAMIENTO (Iteración)    ║")
        print(f"╠════════════════════════════════╦═════════════╣")
        for nombre, valor in tabla:
            print(f"║ {nombre:<30} ║ {valor:>11} ║")
        print(f"╚════════════════════════════════╩═════════════╝")

def crear_entorno():
    """Función factoría para crear una instancia del entorno."""
    try:
        df = pd.read_csv(RUTA_DATOS)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        return EntornoTradingBitgetV2(df)
    except Exception as e:
        print(f"❌ Error creando entorno hijo: {e}")
        raise e

def main():
    print(f"🚀 INICIANDO ENTRENAMIENTO TURBO-PARALELO")
    print(f"========================================")
    print(f"🔥 NÚCLEOS CPU: {N_ENVS}")
    print(f"🔥 DISPOSITIVO: {DISPOSITIVO} (GPU)")
    print(f"📂 DATOS: {RUTA_DATOS}")
    
    # Crear directorios
    os.makedirs(DIR_MODELOS, exist_ok=True)
    os.makedirs(DIR_LOGS, exist_ok=True)

    # 1. CREACIÓN DEL VECTOR DE ENTORNOS
    print("⚙️ Inicializando entornos paralelos...")
    env = make_vec_env(
        crear_entorno, 
        n_envs=N_ENVS, 
        vec_env_cls=CONTROLADOR_VEHICULO
    )

    # 2. DEFINICIÓN DEL AGENTE
    modelo = PPO(
        "MlpPolicy",
        env,
        verbose=0,              # 🔇 DESACTIVAMOS LOGS EN INGLÉS
        device=DISPOSITIVO,
        tensorboard_log=DIR_LOGS,
        batch_size=4096,        
        n_steps=1024,           
        n_epochs=10,            
        learning_rate=3e-4,     
        ent_coef=0.01,          
        gamma=0.99,             
    )

    # 3. CALLBACKS
    checkpoint_callback = CheckpointCallback(
        save_freq=100000 // N_ENVS,
        save_path=DIR_MODELOS,
        name_prefix="ppo_turbo"
    )
    
    # Notificador usa hooks internos de SB3 (on_rollout_start) para pillar los datos frescos
    notificador_es = NotificadorEspañol(check_freq=1) 

    print("\n🧠 INICIANDO APRENDIZAJE (EN ESPAÑOL)...")
    try:
        modelo.learn(
            total_timesteps=PASOS_TOTALES, 
            callback=[checkpoint_callback, notificador_es], 
            progress_bar=True  # ✅ BARRA DE PROGRESO ACTIVADA
        )
        print("✅ ENTRENAMIENTO FINALIZADO CON ÉXITO.")
        
        # Guardar modelo final
        ruta_final = os.path.join(DIR_MODELOS, "modelo_final_turbo")
        modelo.save(ruta_final)
        print(f"💾 Modelo guardado en: {ruta_final}")

    except KeyboardInterrupt:
        print("\n⚠️ ENTRENAMIENTO INTERRUMPIDO POR USUARIO.")
        modelo.save(os.path.join(DIR_MODELOS, "modelo_interrumpido"))
        print("💾 Guardado de emergencia completado.")
    finally:
        env.close()

if __name__ == "__main__":
    main()
