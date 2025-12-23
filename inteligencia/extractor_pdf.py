
import sys
import subprocess

def intentar_instalar_pypdf():
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf"])
        print("✅ Librería pypdf instalada automáticamente.")
        return True
    except:
        print("❌ No se pudo instalar pypdf automáticamente.")
        return False

def extraer_texto_pdf(ruta_archivo):
    """
    Intenta extraer texto usando pypdf.
    Si falta la librería, intenta instalarla o deja instrucción.
    """
    try:
        import pypdf
    except ImportError:
        print("💡 pypdf no detectado. Intentando instalar...")
        if not intentar_instalar_pypdf():
            return "ERROR_MISSING_PYPDF: Ejecuta 'pip install pypdf'"
        import pypdf

    try:
        texto = ""
        reader = pypdf.PdfReader(ruta_archivo)
        for page in reader.pages:
            t = page.extract_text()
            if t: texto += t + "\n"
        return texto
    except Exception as e:
        print(f"⚠️ Error leyendo PDF {ruta_archivo}: {e}")
        return None
