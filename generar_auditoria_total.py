import os
import shutil
import json
import hashlib
import re
import datetime
import subprocess
import zipfile
from pathlib import Path

# CONFIGURACIÓN
ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) # zerox-core
OUTPUT_BASE = os.path.join(ROOT_DIR, "tmp", "AUDITORIA_TOTAL_CHATGPT")
ZIPS_DIR = os.path.join(ROOT_DIR, "tmp", "AUDITORIA_TOTAL_CHATGPT_ZIPS")
PROJECT_COPY_DIR = os.path.join(OUTPUT_BASE, "PROYECTO")
LOGS_COPY_DIR = os.path.join(OUTPUT_BASE, "LOGS")

MAX_FILE_SIZE_MB = 25
LARGE_FOLDER_LIMIT_MB = 200

EXCLUDE_DIRS = {
    "node_modules", "dist", "build", ".next", "out", 
    ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache", 
    ".git", ".idea", ".vscode", "tmp" # Exclude tmp itself to avoid recursion
}
EXCLUDE_EXTENSIONS = {".exe", ".dll", ".bin", ".iso", ".mp4", ".mkv", ".mov"}
SECRET_PATTERNS = [
    (r'(?i)(api_key|secret|token|password|passphrase)\s*[:=]\s*[\'"]?([a-zA-Z0-9_\-]{20,})[\'"]?', r'\1: "***REDACTADO***"'),
    (r'(AIza[0-9A-Za-z-_]{35})', r'***REDACTADO_GOOGLE_KEY***'),
    (r'(sk-proj-[a-zA-Z0-9]{20,})', r'***REDACTADO_OPENAI_KEY***')
]

# ESTADO
manifest = []
excluidos = []
secretos_redactados = []
stats = {"files_included": 0, "bytes_included": 0, "redacted_count": 0}

def sha256_checksum(filename, block_size=65536):
    sha256 = hashlib.sha256()
    try:
        with open(filename, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                sha256.update(block)
        return sha256.hexdigest()
    except:
        return "ERROR_READING"

def is_secret_file(filename):
    return filename == ".env"

def redact_content(content, filepath):
    original_content = content
    modified = False
    
    for pattern, replacement in SECRET_PATTERNS:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            modified = True
            
    if modified:
        secretos_redactados.append(f"{os.path.basename(filepath)} matched key pattern")
        stats["redacted_count"] += 1
        
    return content

def get_folder_size(path):
    total = 0
    for entry in os.scandir(path):
        if entry.is_file():
            total += entry.stat().st_size
        elif entry.is_dir():
            total += get_folder_size(entry.path)
    return total

def process_directory(src, dst):
    if not os.path.exists(dst):
        os.makedirs(dst)
        
    for item in os.listdir(src):
        s_item = os.path.join(src, item)
        d_item = os.path.join(dst, item)
        
        # EXCLUSIONES DE DIRECTORIO
        if os.path.isdir(s_item):
            if item in EXCLUDE_DIRS:
                excluidos.append({"path": s_item, "reason": "EXCLUDED_DIR_PATTERN"})
                continue
            
            # Check size for knowledge folders
            if "conocimiento" in s_item.lower() or "biblioteca" in s_item.lower():
                size_mb = get_folder_size(s_item) / (1024*1024)
                if size_mb > LARGE_FOLDER_LIMIT_MB:
                    excluidos.append({"path": s_item, "reason": f"LARGE_KNOWLEDGE_FOLDER (> {LARGE_FOLDER_LIMIT_MB}MB)"})
                    with open(os.path.join(dst, "CONOCIMIENTO_NO_INCLUIDO.txt"), "w") as f:
                        f.write(f"Folder {item} excluded due to size ({size_mb:.2f} MB). Included in manifest only.")
                    continue

            process_directory(s_item, d_item)
            
        # PROCESAR ARCHIVOS
        elif os.path.isfile(s_item):
            # EXCLUSIONES POR EXTENSIÓN
            ext = os.path.splitext(item)[1].lower()
            if ext in EXCLUDE_EXTENSIONS:
                excluidos.append({"path": s_item, "reason": "EXCLUDED_EXTENSION"})
                continue
                
            # EXCLUSIÓN .ENV
            if item == ".env":
                excluidos.append({"path": s_item, "reason": "SECRET_FILE_ENV"})
                # Create .env.example if not exists
                example_path = os.path.join(dst, ".env.example")
                try:
                    with open(s_item, 'r', encoding='utf-8') as f_env:
                        lines = f_env.readlines()
                    with open(example_path, 'w', encoding='utf-8') as f_ex:
                        for line in lines:
                            if '=' in line and not line.strip().startswith('#'):
                                key = line.split('=')[0]
                                f_ex.write(f"{key}=***REDACTADO***\n")
                            else:
                                f_ex.write(line)
                    manifest.append({
                        "ruta_relativa": os.path.relpath(example_path, OUTPUT_BASE),
                        "tamano_bytes": os.path.getsize(example_path),
                        "fecha_modif": datetime.datetime.now().isoformat(),
                        "sha256": sha256_checksum(example_path)
                    })
                except Exception as e:
                    print(f"Error making .env.example: {e}")
                continue

            # CHECK SIZE
            size_bytes = os.path.getsize(s_item)
            if size_bytes > MAX_FILE_SIZE_MB * 1024 * 1024:
                excluidos.append({"path": s_item, "reason": f"FILE_TOO_LARGE (>{MAX_FILE_SIZE_MB}MB)"})
                continue
            
            # PROCESAR ARCHIVO VALIDADO
            try:
                # Intento leer como texto para redactar
                is_text = False
                try:
                    with open(s_item, 'r', encoding='utf-8') as f:
                        content = f.read()
                    is_text = True
                except:
                    is_text = False # Binary file
                
                if is_text:
                    content_redacted = redact_content(content, input_path := s_item)
                    with open(d_item, 'w', encoding='utf-8') as f:
                        f.write(content_redacted)
                else:
                    shutil.copy2(s_item, d_item)
                
                # Add to manifest
                rel_path = os.path.relpath(d_item, OUTPUT_BASE)
                manifest.append({
                    "ruta_relativa": rel_path,
                    "tamano_bytes": os.path.getsize(d_item),
                    "fecha_modif": datetime.datetime.fromtimestamp(os.path.getmtime(d_item)).isoformat(),
                    "sha256": sha256_checksum(d_item)
                })
                
                stats["files_included"] += 1
                stats["bytes_included"] += size_bytes
                
            except Exception as e:
                print(f"Error copying {s_item}: {e}")
                excluidos.append({"path": s_item, "reason": f"COPY_ERROR ({str(e)})"})

def main():
    print("🚀 INICIANDO AUDITORÍA TOTAL...")
    
    # 0. Limpieza (Soft + Try Except)
    if os.path.exists(OUTPUT_BASE):
        try: shutil.rmtree(OUTPUT_BASE)
        except: pass
    if not os.path.exists(PROJECT_COPY_DIR): os.makedirs(PROJECT_COPY_DIR)
    if not os.path.exists(LOGS_COPY_DIR): os.makedirs(LOGS_COPY_DIR)
    
    if not os.path.exists(ZIPS_DIR):
        os.makedirs(ZIPS_DIR)
    
    # 1. Copiar Proyecto Recursivo
    print("📂 Copiando archivos del proyecto...")
    process_directory(ROOT_DIR, PROJECT_COPY_DIR)
    
    # 2. Copiar Logs Críticos
    print("📝 Recopilando Logs...")
    logs_to_copy = [
        os.path.join(ROOT_DIR, "tmp", "zerox_watchdog.txt"),
        os.path.join(ROOT_DIR, "tmp", "zerox_core_stderr.log"),
        os.path.join(ROOT_DIR, "tmp", "zerox_crash_report.txt"),
        os.path.join(ROOT_DIR, "tmp", "zerox_exception_trace.txt"),
        os.path.join(ROOT_DIR, "inteligencia", "heartbeat.json"),
        os.path.join(ROOT_DIR, "inteligencia", "estado_runtime.json"),
        os.path.join(ROOT_DIR, "inteligencia", "logs_cerebro.txt"),
        os.path.join(ROOT_DIR, "tmp", "ZER0X_PARA_PEGAR_A_CHATGPT.txt") # Incluir el reporte final
    ]
    
    for log_path in logs_to_copy:
        if os.path.exists(log_path):
            try:
                dest = os.path.join(LOGS_COPY_DIR, os.path.basename(log_path))
                # Special handling for huge logs
                if "logs_cerebro.txt" in log_path and os.path.getsize(log_path) > 5*1024*1024:
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    with open(dest, 'w', encoding='utf-8') as f:
                        f.writelines(lines[-1000:]) # Last 1000 lines
                else:
                    shutil.copy2(log_path, dest)
            except Exception as e:
                print(f"Error copying log {log_path}: {e}")

    # 3. Generar 00_ARBOL_COMPLETO.txt
    print("🌳 Generando árbol de directorio...")
    try:
        # tree command needs shell
        tree_path = os.path.join(OUTPUT_BASE, "00_ARBOL_COMPLETO.txt")
        result = subprocess.run(f"tree /F /A \"{PROJECT_COPY_DIR}\"", shell=True, capture_output=True, text=True)
        with open(tree_path, "w", encoding="utf-8") as f:
            f.write(result.stdout)
    except Exception as e:
        print(f"Error running tree: {e}")

    # 4. JSON Manifests
    print("📊 Generando manifestos JSON...")
    with open(os.path.join(OUTPUT_BASE, "01_MANIFEST_ARCHIVOS.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    with open(os.path.join(OUTPUT_BASE, "02_EXCLUIDOS.json"), "w", encoding="utf-8") as f:
        json.dump(excluidos, f, indent=2)
        
    with open(os.path.join(OUTPUT_BASE, "04_SECRETOS_REDACTADOS.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(secretos_redactados))

    # 5. Generar Resumen
    summary_path = os.path.join(OUTPUT_BASE, "03_RESUMEN_PARA_PEGAR.txt")
    summary_content = f"""
============================================================
              AUDITORÍA ZEROX - RESUMEN EJECUTIVO
============================================================
FECHA: {datetime.datetime.now().isoformat()}
RUTA ORIGINAL: {ROOT_DIR}
ARCHIVOS INCLUIDOS: {stats['files_included']}
BYTES TOTALES: {stats['bytes_included']:,}
ARCHIVOS EXCLUIDOS: {len(excluidos)}
SECRETOS REDACTADOS: {stats['redacted_count']} instance(s)

ARCHIVOS CRÍTICOS INCLUIDOS:
- 00_ARBOL_COMPLETO.txt
- 01_MANIFEST_ARCHIVOS.json
- 02_EXCLUIDOS.json
- Logs Recientes (Crash Reports, Watchdog, Heartbeat)
- Código Fuente Completo (Python, JS, Configs)

EXCLUSIONES MAYORES:
{json.dumps([e['path'] for e in excluidos if 'LARGE' in e['reason']], indent=2)}

INSTRUCCIONES:
Este paquete contiene el código fuente completo y limpio de ZEROX.
Suba los ZIPs generados a la herramienta de análisis.
============================================================
"""
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_content)

    # 6. COMPRIMIR Y SPLIT
    print("📦 Comprimiendo ZIPs...")
    
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = os.path.join(ZIPS_DIR, f"AUDITORIA_TOTAL_CHATGPT_{timestamp_str}.zip")
    
    # Create valid zip
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(OUTPUT_BASE):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, OUTPUT_BASE)
                zipf.write(file_path, arcname)

    # Check size and split if needed (Simple chunking)
    zip_size = os.path.getsize(zip_filename)
    MAX_SIZE = 90 * 1024 * 1024 # 90MB
    
    if zip_size > MAX_SIZE:
        print(f"⚠️ ZIP gigante ({zip_size/1024/1024:.2f}MB). Dividiendo...")
        # Simple file splitting binary
        with open(zip_filename, 'rb') as src:
            part_num = 1
            while True:
                chunk = src.read(MAX_SIZE)
                if not chunk: break
                part_name = os.path.join(ZIPS_DIR, f"AUDITORIA_TOTAL_CHATGPT_{timestamp_str}.part{part_num:02d}.zip")
                with open(part_name, 'wb') as dst:
                    dst.write(chunk)
                print(f"   -> Generado {part_name}")
                part_num += 1
        
        # Safe Remove
        try: os.remove(zip_filename) 
        except: print("⚠️ lock al borrar original, no pasa nada.")
    else:
        print(f"✅ ZIP único generado: {zip_filename}")

    # Append zip paths to summary
    with open(summary_path, "a", encoding="utf-8") as f:
        f.write("\nARCHIVOS ZIP GENERADOS:\n")
        # List ONLY matching timestamp to avoid listing old parts
        for z in os.listdir(ZIPS_DIR):
            if timestamp_str in z:
                 f.write(f"- {os.path.join(ZIPS_DIR, z)}\n")

    print("✅ PROCESO COMPLETADO.")

if __name__ == "__main__":
    main()
