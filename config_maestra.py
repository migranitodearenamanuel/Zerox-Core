import os
import sys
import subprocess
import requests
import time

# =============================================================================
# 🛠️ ZEROX CONFIGURACIÓN TOTAL - REPARACIÓN Y BLINDAJE
# Este script verifica que todo esté instalado correctamente.
# =============================================================================

def imprimir_paso(mensaje):
    """Imprime un mensaje de paso en azul."""
    print(f"\n🔵 {mensaje}")

def imprimir_exito(mensaje):
    """Imprime un mensaje de éxito en verde."""
    print(f"✅ {mensaje}")

def imprimir_error(mensaje):
    """Imprime un mensaje de error en rojo."""
    print(f"❌ {mensaje}")

def imprimir_advertencia(mensaje):
    """Imprime una advertencia en amarillo."""
    print(f"⚠️ {mensaje}")

def ejecutar_comando(comando):
    """Ejecuta un comando de sistema y devuelve True si funcionó."""
    try:
        subprocess.check_call(comando, shell=True)
        return True
    except subprocess.CalledProcessError:
        return False

def reparar_torch_gpu():
    """
    Intenta arreglar la instalación de PyTorch para que use la tarjeta gráfica (GPU).
    Esto es crucial para que la IA vaya rápido.
    """
    imprimir_paso("🔥 REPARANDO INSTALACIÓN DE GPU (NVIDIA)...")
    
    # 1. Desinstalar versiones basura o incorrectas
    print("   - Limpiando versiones antiguas de Torch...")
    ejecutar_comando(f"{sys.executable} -m pip uninstall -y torch torchvision torchaudio")

    # 2. Instalar versión CUDA 12.1 (Compatible con RTX 2070 y modernas)
    print("   - Instalando PyTorch con soporte CUDA (Esto tardará un poco)...")
    # Usamos --no-cache-dir para forzar descarga nueva desde internet
    comando = f"{sys.executable} -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121"
    if ejecutar_comando(comando):
        imprimir_exito("PyTorch GPU instalado correctamente.")
    else:
        imprimir_error("Fallo al instalar PyTorch GPU. Se intentará continuar (la IA podría ir lenta).")

def instalar_dependencias():
    """Instala el resto de librerías necesarias desde requisitos.txt"""
    imprimir_paso("Instalando Resto de Dependencias...")
    # Instalamos requisitos.txt normal (sin torch, que ya lo instalamos arriba)
    if os.path.exists("requisitos.txt"):
        comando = f"{sys.executable} -m pip install -r requisitos.txt"
        if ejecutar_comando(comando):
            imprimir_exito("Librerías Core instaladas.")
        else:
            imprimir_error("Error instalando algunas librerías. Verifica tu conexión a internet.")
    else:
        imprimir_advertencia("No se encontró 'requisitos.txt'.")

def verificar_gpu():
    """Comprueba si Python puede ver tu tarjeta gráfica NVIDIA."""
    imprimir_paso("Verificando Estado de GPU...")
    try:
        import torch
        if torch.cuda.is_available():
            nombre_gpu = torch.cuda.get_device_name(0)
            print(f"\033[92m✅ NVIDIA RTX DETECTADA: {nombre_gpu}\033[0m") 
            print(f"   VRAM (Memoria de Video): {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
            print("   Versión CUDA: " + torch.version.cuda)
            return True
        else:
            imprimir_advertencia("⚠️ NO SE DETECTA GPU. ¿Tienes los drivers de NVIDIA instalados?")
            print("   Versión Torch instalada: " + torch.__version__)
            return False
    except ImportError:
        imprimir_error("PyTorch no parece estar instalado correctamente.")
        return False

def verificar_ollama():
    """Verifica si el servidor de IA local (Ollama) está corriendo."""
    imprimir_paso("Verificando Ollama (IA Local)...")
    try:
        respuesta = requests.get("http://localhost:11434")
        if respuesta.status_code == 200:
            imprimir_exito("Ollama ONLINE (Listo para pensar).")
        else:
            imprimir_advertencia(f"Ollama responde con código extraño: {respuesta.status_code}")
    except:
        imprimir_error("Ollama OFFLINE. Ejecuta 'ollama run deepseek-r1:8b' en otra terminal antes de empezar.")

def crear_directorios():
    """Crea las carpetas necesarias si no existen."""
    imprimir_paso("Creando Estructura de Carpetas...")
    carpetas = ["memoria_vectorial", "logs", "conocimiento", "nucleo", "inteligencia", "interfaz", "utilidades"]
    for d in carpetas:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"   + Carpeta creada: {d}")

def main():
    print("===================================================")
    print("   🚀 ZEROX - REPARACIÓN DE SISTEMA")
    print("===================================================")

    # 1. Reparar Torch GPU primero
    reparar_torch_gpu()

    # 2. Instalar resto de cosas
    instalar_dependencias()

    # 3. Verificar todo
    verificar_gpu()
    verificar_ollama()
    crear_directorios()

    print("\n===================================================")
    print("✅ PROCESO FINALIZADO.")
    print("   Si ves 'NVIDIA RTX DETECTADA', ejecuta LANZAR_TODO.bat")
    print("===================================================")

if __name__ == "__main__":
    main()
