import os
import json

# Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(BASE_DIR, "..")
ENTORNO_PATH = os.path.join(ROOT_DIR, "inteligencia", "entorno_trading_v2.py")
OUTPUT_DIR = os.path.join(ROOT_DIR, "KAGGLE_PACK")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Leer contenido del entorno
with open(ENTORNO_PATH, "r", encoding="utf-8") as f:
    codigo_entorno = f.read()

# Código de Entrenamiento adaptado para Kaggle
codigo_entrenamiento = """
import os
import time
import pandas as pd
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback

# --- 1. AUTODETECCIÓN DE DATOS EN KAGGLE ---
print("🔍 Buscando dataset...")
RUTA_DATOS = None
for dirname, _, filenames in os.walk('/kaggle/input'):
    for filename in filenames:
        if filename.endswith('.csv'):
            RUTA_DATOS = os.path.join(dirname, filename)
            print(f"✅ Encontrado: {RUTA_DATOS}")
            break

if not RUTA_DATOS:
    print("❌ NO SE ENCUENTRA EL CSV. Sube 'conjunto_datos_maestro_v2.csv' como dataset.")
else:
    print(f"📂 Usando: {RUTA_DATOS}")

# --- 2. CONFIGURACIÓN ---
N_ENVS = 4 
PASOS_TOTALES = 10_000_000 
DISPOSITIVO = "cuda"

# --- 3. DEFINICIÓN DEL ENTORNO (Pegado arriba) ---
# (La clase EntornoTradingBitgetV2 ya debe estar definida en la celda anterior)

def crear_entorno():
    try:
        df = pd.read_csv(RUTA_DATOS)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        return EntornoTradingBitgetV2(df)
    except Exception as e:
        print(f"❌ Error creando entorno hijo: {e}")
        raise e

# --- 4. CALLBACK ESPAÑOL ---
class NotificadorEspañol(BaseCallback):
    def __init__(self, check_freq: int, verbose=1):
        super(NotificadorEspañol, self).__init__(verbose)
        self.check_freq = check_freq
        self.start_time = time.time()

    def _on_step(self) -> bool:
        if self.n_calls % self.check_freq == 0:
            elapsed = time.time() - self.start_time
            fps = int(self.num_timesteps / elapsed) if elapsed > 0 else 0
            print(f"🇪🇸 Pasos: {self.num_timesteps} | FPS: {fps}")
        return True

# --- 5. EJECUCIÓN ---
if __name__ == "__main__" and RUTA_DATOS:
    print("🚀 INICIANDO ENTRENAMIENTO EN KAGGLE (GPU)...")
    
    # Crear vector de entornos (USANDO DUMMYVECENV PARA EVITAR ERRORES MULTIPROCESO)
    env = make_vec_env(crear_entorno, n_envs=N_ENVS, vec_env_cls=DummyVecEnv)

    modelo = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        device=DISPOSITIVO,
        batch_size=4096,
        n_steps=2048, # Aumentado para mayor estabilidad
        learning_rate=3e-4,
        ent_coef=0.01,
        gamma=0.99,
    )
    
    modelo.learn(total_timesteps=PASOS_TOTALES, progress_bar=True)
    
    modelo.save("modelo_zerox_kaggle_final")
    print("💾 Modelo guardado como 'modelo_zerox_kaggle_final.zip'")
    
    # Comprimir para descarga fácil
    import shutil
    shutil.make_archive("resultado_entrenamiento", 'zip', ".", "modelo_zerox_kaggle_final.zip")
    print("📦 Listo para descargar: resultado_entrenamiento.zip")
"""

# Construir Notebook JSON
notebook = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# 🧠 ZEROX CORE - ENTRENAMIENTO EN LA NUBE (KAGGLE)\n",
    "Este notebook entrena a la IA usando las GPUs de Google.\n",
    "### Instrucciones:\n",
    "1. Asegúrate de haber subido el archivo `.csv` en 'Add Data'.\n",
    "2. Activa la GPU en los ajustes del Notebook (Accelerator: GPU T4 x2 o P100).\n",
    "3. Ejecuta todas las celdas."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "!pip install stable-baselines3==2.3.2 shimmy pandas ta gymnasium tensorboard==2.15.1 protobuf==3.20.3"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": codigo_entorno.splitlines(keepends=True) # Insertamos código del entorno
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": codigo_entrenamiento.splitlines(keepends=True) # Insertamos script entrenamiento
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.10.12"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}

# Guardar Notebook
nb_path = os.path.join(OUTPUT_DIR, "ZEROX_KAGGLE.ipynb")
with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1)

print(f"✅ Notebook generado en: {nb_path}")

# Copiar dataset para facilitar
import shutil
src_csv = os.path.join(ROOT_DIR, "datos", "conjunto_datos_maestro_v2.csv")
dst_csv = os.path.join(OUTPUT_DIR, "conjunto_datos_maestro_v2.csv")
try:
    shutil.copy(src_csv, dst_csv)
    print(f"✅ Dataset copiado a: {dst_csv}")
except:
    print("⚠️ No se encontró el dataset original para copiarlo.")
