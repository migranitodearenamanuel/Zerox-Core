import subprocess
import time
import sys
import os
import requests
from dotenv import load_dotenv

# Importar "a la fuerza" el módulo de inteligencia desde la raíz
sys.path.append(os.path.join(os.path.dirname(__file__), 'inteligencia'))
try:
    import puente_visual
except ImportError:
    puente_visual = None

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")
# Ruta corregida tras la migración
SCRIPT_MAESTRO = os.path.join("inteligencia", "operador_maestro.py")

def notificar(mensaje):
    print(mensaje)
    # 1. Disco
    if WEBHOOK:
        try:
            requests.post(WEBHOOK, json={"content": mensaje})
        except: pass
    
    # 2. UI
    if puente_visual:
        puente_visual.actualizar_estado({
            "estado_sistema": "REINICIANDO ⚠️",
            "ultima_notificacion": mensaje,
            "color_estado": "amarillo"
        })

def verificar_ollama():
    """Verifica si Ollama está corriendo, si no, intenta lanzarlo."""
    print("🧠 [PERRO GUARDIAN] Verificando motor de IA (Ollama)...")
    try:
        # Check rápido a la API
        requests.get("http://localhost:11434", timeout=1)
        print("✅ Ollama está ONLINE.")
        return True
    except:
        print("⚠️ Ollama está APAGADO. Iniciando servidor...")
        try:
            # Lanzar en segundo plano sin esperar
            subprocess.Popen(["ollama", "serve"], creationflags=subprocess.CREATE_NEW_CONSOLE)
            print("⏳ Esperando arranque de Ollama (10s)...")
            time.sleep(10)
            return True
        except Exception as e:
            print(f"❌ ERROR CRÍTICO: No se pudo iniciar Ollama: {e}")
            print("   Asegúrate de tener Ollama instalado y en el PATH.")
            return False

def lanzar_bot():
    verificar_ollama() # Check previo al bucle
    intentos = 0
    while True:
        msg = f"\n🚀 [PERRO GUARDIAN] Lanzando ZEROX (Intento #{intentos+1})..."
        print(msg)
        if puente_visual:
            puente_visual.actualizar_estado({"estado_sistema": "INICIANDO 🔄"})

        # Subproceso
        proceso = subprocess.Popen([sys.executable, SCRIPT_MAESTRO])
        codigo = proceso.wait()
        
        if codigo != 0:
            err = f"⚠️ [PERRO GUARDIAN] Bot caído (Código {codigo}). Reinicio en 5s..."
            notificar(err)
            time.sleep(5)
            intentos += 1
        else:
            print("✅ Parada limpia.")
            if puente_visual: puente_visual.actualizar_estado({"estado_sistema": "DETENIDO ⚪"})
            break

if __name__ == "__main__":
    try:
        lanzar_bot()
    except KeyboardInterrupt:
        print("\n🛑 PERRO GUARDIAN DETENIDO.")
