import pandas as pd
import os
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import EvalCallback
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv
import functools
from entorno_trading_v2 import EntornoTradingBitgetV2

# --- CONFIGURACIÓN FASE 2 ---
ARCHIVO_DATOS = '../datos/conjunto_datos_maestro_v2.csv'
DIR_LOGS = './logs_v2_turbo' 
DIR_MODELOS = './modelos_v2_turbo'
TOTAL_PASOS = 2_000_000 
N_ENTORNOS = 8 

# Hiperparámetros PPO V2
PARAMETROS_PPO = {
    'n_steps': 2048 // N_ENTORNOS, 
    'batch_size': 2048,
    'learning_rate': 3e-4,
    'ent_coef': 0.05,
    'gamma': 0.99,
    'gae_lambda': 0.95,
    'clip_range': 0.2,
    'device': 'cuda',
    'verbose': 1,
    'tensorboard_log': DIR_LOGS,
    'policy_kwargs': {
        'net_arch': dict(pi=[256, 256, 256], vf=[256, 256, 256])
    }
}

# Función Global para Multiprocesamiento
def crear_entorno_fn(df, rango, semilla=0, dir_logs=None):
    """
    Función de utilidad para entornos multiproceso.
    """
    def _iniciar():
        from entorno_trading_v2 import EntornoTradingBitgetV2 
        from stable_baselines3.common.monitor import Monitor
        env = EntornoTradingBitgetV2(df)
        env.reset(seed=semilla + rango)
        # Añadir Monitor para logs
        if dir_logs is not None:
             env = Monitor(env, filename=os.path.join(dir_logs, str(rango)))
        else:
             env = Monitor(env)
        return env
    return _iniciar

def entrenar():
    # 1. Cargar Datos V2
    if not os.path.exists(ARCHIVO_DATOS):
        print(f"❌ Error: No se encuentra {ARCHIVO_DATOS}")
        return

    print("📊 Cargando DATASET MAESTRO V2 (Precios + Sentimiento)...")
    df = pd.read_csv(ARCHIVO_DATOS)
    
    # Dividir Entrenamiento/Evaluación (80/20)
    indice_division = int(len(df) * 0.8)
    df_entrenamiento = df.iloc[:indice_division]
    df_evaluacion = df.iloc[indice_division:]
    
    print(f"🧠 Datos Entrenamiento: {len(df_entrenamiento)} velas")
    
    # 2. Crear Entornos Paralelos (MODO TURBO)
    print(f"⚡ Activando MODO TURBO: {N_ENTORNOS} Entornos Paralelos...")
    
    fns_entorno = [crear_entorno_fn(df_entrenamiento, i, dir_logs=DIR_LOGS) for i in range(N_ENTORNOS)]
    env = SubprocVecEnv(fns_entorno)
    
    # Entorno de evaluación (Serial)
    fns_entorno_eval = [crear_entorno_fn(df_evaluacion, 0, dir_logs=None)]
    env_eval = SubprocVecEnv(fns_entorno_eval)

    # 3. Callbacks
    os.makedirs(DIR_MODELOS, exist_ok=True)
    
    callback_eval = EvalCallback(
        env_eval,
        best_model_save_path=DIR_MODELOS,
        log_path=DIR_LOGS,
        eval_freq=10000 // N_ENTORNOS,
        deterministic=True,
        render=False
    )

    # 4. Inicializar Agente
    print(f"🔥 Inicializando Agente V2 (Red Separada 256x3) en {torch.cuda.get_device_name(0)}...")
    modelo = PPO('MlpPolicy', env, **PARAMETROS_PPO)

    # 5. Entrenar
    print("🚀 LANZANDO FASE 2: Entorno Multimodal (Español)...")
    try:
        modelo.learn(total_timesteps=TOTAL_PASOS, callback=callback_eval, progress_bar=True)
        print("✅ Fase 2 Finalizada.")
        modelo.save(f"{DIR_MODELOS}/ppo_v2_final")
        
    except KeyboardInterrupt:
        print("\n⚠️ Entrenamiento interrumpido. Guardando estado...")
        modelo.save(f"{DIR_MODELOS}/ppo_v2_interrumpido")

if __name__ == "__main__":
    if torch.cuda.is_available():
        print(f"✅ GPU Activa: {torch.cuda.get_device_name(0)}")
    else:
        print("⚠️ PRECAUCIÓN: Usando CPU (Lento)")
    
    entrenar()
