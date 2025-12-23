import pandas as pd
import os
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import EvalCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv

# Importar nuestro entorno personalizado
from trading_env import BitgetTradingEnv

# --- CONFIGURACIÓN ---
DATA_FILE = '../data/btc_usdt_15m.csv'
LOG_DIR = './logs'
MODEL_DIR = './modelos'
TOTAL_TIMESTEPS = 1_000_000 # 1 Millón de pasos para empezar

# Hiperparámetros PPO (Optimizados para RTX 2070 / 32GB RAM)
PPO_PARAMS = {
    'n_steps': 4096,        # Pasos por actualización (Horizonte largo)
    'batch_size': 2048,     # Gran batch para GPU
    'ent_coef': 0.01,       # Exploración inicial
    'learning_rate': 3e-4,  # Tasa de aprendizaje estándar
    'device': 'cuda',       # USAR GPU
    'verbose': 1,
    'tensorboard_log': LOG_DIR,
    'policy_kwargs': {
        'net_arch': [512, 512, 512] # Red profunda (Deep Network)
    }
}

def train():
    # 1. Cargar Datos
    if not os.path.exists(DATA_FILE):
        print(f"❌ Error: No se encuentra {DATA_FILE}. Ejecuta data_harvester.py primero.")
        return

    print("📊 Cargando dataset...")
    df = pd.read_csv(DATA_FILE)
    
    # Split Train/Eval (80/20)
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    eval_df = df.iloc[split_idx:]
    
    print(f"🧠 Datos de Entrenamiento: {len(train_df)} velas")
    print(f"🧪 Datos de Evaluación: {len(eval_df)} velas")

    # 2. Crear Entornos
    # Entorno de entrenamiento
    env = BitgetTradingEnv(train_df)
    env = Monitor(env) # Para logs básicos
    env = DummyVecEnv([lambda: env]) # Vectorizado (necesario para SB3)

    # Entorno de evaluación
    eval_env = BitgetTradingEnv(eval_df)
    eval_env = Monitor(eval_env)
    eval_env = DummyVecEnv([lambda: eval_env])

    # 3. Callbacks
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # EvalCallback: Evalúa el modelo cada 10,000 pasos y guarda el mejor
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=MODEL_DIR,
        log_path=LOG_DIR,
        eval_freq=10000,
        deterministic=True,
        render=False
    )

    # 4. Inicializar Agente PPO
    print(f"🔥 Inicializando Agente PPO en {torch.cuda.get_device_name(0)}...")
    model = PPO('MlpPolicy', env, **PPO_PARAMS)

    # 5. Entrenar
    print("🚀 Iniciando entrenamiento masivo...")
    try:
        model.learn(total_timesteps=TOTAL_TIMESTEPS, callback=eval_callback, progress_bar=True)
        print("✅ Entrenamiento finalizado.")
        
        # Guardar modelo final
        model.save(f"{MODEL_DIR}/ppo_bitget_final")
        print(f"💾 Modelo final guardado en {MODEL_DIR}/ppo_bitget_final.zip")
        
    except KeyboardInterrupt:
        print("\n⚠️ Entrenamiento interrumpido por usuario. Guardando estado actual...")
        model.save(f"{MODEL_DIR}/ppo_bitget_interrupted")

if __name__ == "__main__":
    # Verificar CUDA
    if torch.cuda.is_available():
        print(f"✅ CUDA Disponible: {torch.cuda.get_device_name(0)}")
    else:
        print("⚠️ ADVERTENCIA: CUDA no detectado. El entrenamiento será lento en CPU.")
    
    train()
