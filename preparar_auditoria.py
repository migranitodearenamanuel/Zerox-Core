import os
import shutil
import zipfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(BASE_DIR, "tmp")
TARGET_DIR = os.path.join(TMP_DIR, "AUDITORIA_CHATGPT")
ZIP_FILE = os.path.join(TMP_DIR, "AUDITORIA_CHATGPT") # make_archive adds .zip extension

DIRECTORIES_TO_INCLUDE = ["electron", "interfaz", "inteligencia"]
FILES_TO_INCLUDE = ["package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "requirements.txt", "pyproject.toml", "README.md"]
LOG_EXTENSIONS = [".log", ".txt", ".json", ".diff"]

EXCLUDE_DIRS = ["node_modules", "dist", "build", "__pycache__", "venv", ".git", ".idea", ".vscode"]
EXCLUDE_FILES = [".env", ".DS_Store"]

def clean_and_prepare():
    if os.path.exists(TARGET_DIR):
        shutil.rmtree(TARGET_DIR)
    os.makedirs(TARGET_DIR)
    os.makedirs(os.path.join(TARGET_DIR, "tmp"), exist_ok=True)

def copy_project_files():
    # 1. Directorios Principales
    for dirname in DIRECTORIES_TO_INCLUDE:
        src = os.path.join(BASE_DIR, dirname)
        dst = os.path.join(TARGET_DIR, dirname)
        if os.path.exists(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*EXCLUDE_DIRS, *EXCLUDE_FILES))
            print(f"✅ Copiado: {dirname}")

    # 2. Archivos Raíz
    for filename in FILES_TO_INCLUDE:
        src = os.path.join(BASE_DIR, filename)
        dst = os.path.join(TARGET_DIR, filename)
        if os.path.exists(src):
            shutil.copy(src, dst)
            print(f"✅ Copiado: {filename}")

    # 3. Logs Importantes (tmp)
    if os.path.exists(TMP_DIR):
        for f in os.listdir(TMP_DIR):
            if any(f.endswith(ext) for ext in LOG_EXTENSIONS):
                src = os.path.join(TMP_DIR, f)
                dst = os.path.join(TARGET_DIR, "tmp", f)
                if os.path.isfile(src):
                    shutil.copy(src, dst)
        print(f"✅ Copiados logs de /tmp")

def create_env_example():
    env_path = os.path.join(BASE_DIR, ".env")
    example_path = os.path.join(TARGET_DIR, ".env.example")
    
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        
        with open(example_path, "w", encoding="utf-8") as f:
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    f.write(line + "\n")
                    continue
                
                if "=" in line:
                    key = line.split("=")[0]
                    f.write(f"{key}=***REDACTADO***\n")
        print("✅ Creado .env.example (Redactado)")

def create_zip():
    shutil.make_archive(ZIP_FILE, 'zip', TARGET_DIR)
    print(f"📦 ZIP CREADO: {ZIP_FILE}.zip")

if __name__ == "__main__":
    try:
        clean_and_prepare()
        copy_project_files()
        create_env_example()
        create_zip()
    except Exception as e:
        print(f"❌ Error: {e}")
