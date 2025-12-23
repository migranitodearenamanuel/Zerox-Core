import os
import subprocess
import time
from datetime import datetime

import requests

RUTA_REPORTE = os.path.join(os.path.dirname(__file__), "..", "tmp", "zerox_ollama_salud.txt")


def log_salud(mensaje: str):
    timestamp = datetime.now().isoformat()
    linea = f"[{timestamp}] {mensaje}"
    print(linea)
    try:
        os.makedirs(os.path.dirname(RUTA_REPORTE), exist_ok=True)
        with open(RUTA_REPORTE, "a", encoding="utf-8") as f:
            f.write(linea + "\n")
    except Exception:
        pass


def comprobar_ollama():
    url = "http://localhost:11434/api/tags"
    try:
        res = requests.get(url, timeout=2)
        if res.status_code == 200:
            return True, "ONLINE"
        return False, f"HTTP {res.status_code}"
    except Exception as e:
        return False, str(e)


def intentar_arrancar_ollama():
    log_salud("OLLAMA OFFLINE. Intentando arranque automático...")

    comandos = [
        "ollama serve",
        "start ollama serve",
        "C:\\Users\\manue\\AppData\\Local\\Programs\\Ollama\\ollama.exe serve",
    ]

    for cmd in comandos:
        log_salud(f"Ejecutando: {cmd}")
        try:
            if "start" in cmd:
                subprocess.Popen(cmd, shell=True)
            else:
                subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)

            time.sleep(5)
            ok, msg = comprobar_ollama()
            if ok:
                log_salud("OLLAMA ARRANCADO CON ÉXITO.")
                return True
            log_salud(f"Fallo arranque con '{cmd}': {msg}")
        except Exception as e:
            log_salud(f"Error ejecutando comando: {e}")

    return False


def main():
    ok, msg = comprobar_ollama()
    if ok:
        log_salud("OLLAMA ESTADO: ONLINE (Ping OK)")
        return True

    log_salud(f"OLLAMA ESTADO: OFFLINE ({msg})")
    exito = intentar_arrancar_ollama()
    if not exito:
        log_salud("FALLO CRÍTICO: No se pudo revivir a Ollama. El cerebro local seguirá en fallback.")
        return False
    return True


if __name__ == "__main__":
    # PROHIBIDO sys.exit(1) en el core: este script nunca mata el proceso.
    main()

