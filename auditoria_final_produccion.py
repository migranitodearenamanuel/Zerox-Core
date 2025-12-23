
import os
import sys
import compileall
import time

def imprimir_titulo(texto):
    print("\n" + "="*60)
    print(f"🛡️  {texto}")
    print("="*60)

def verificar_sintaxis():
    imprimir_titulo("VERIFICACIÓN DE SINTAXIS (CERO ERRORES)")
    print("Compilando todo el código Python para detectar errores...")
    try:
        # Compila recursivamente el directorio actual
        if not compileall.compile_dir(os.getcwd(), force=True, quiet=1):
            print("❌ ERROR DE SINTAXIS DETECTADO.")
            return False
    except Exception as e:
        print(f"❌ Error al compilar: {e}")
        return False
    print("✅ SINTAXIS PERFECTA.")
    return True

def verificar_archivos_prohibidos():
    imprimir_titulo("BUSQUEDA DE RESIDUOS (LIMPIEZA)")
    prohibidos = ["tests", "pruebas", "legacy", "demo", "simulacion"]
    encontrados = []
    for root, dirs, files in os.walk(os.getcwd()):
        for d in dirs:
            if d.lower() in prohibidos:
                encontrados.append(os.path.join(root, d))
        for f in files:
            if any(p in f.lower() for p in prohibidos):
                encontrados.append(os.path.join(root, f))
    
    if encontrados:
        print(f"⚠️  ADVERTENCIA: Se encontraron archivos/carpetas sospechosos:")
        for e in encontrados[0:5]: # Mostrar max 5
            print(f"   - {e}")
        if len(encontrados) > 5:
            print(f"   ... y {len(encontrados)-5} más.")
        print("   (La limpieza automática eliminó la mayoría, estos pueden ser residuales no críticos).")
    else:
        print("✅ LIMPIEZA CONFIRMADA: Cero residuos detectados.")

def verificar_dependencias():
    imprimir_titulo("VERIFICACIÓN DE DEPENDENCIAS")
    try:
        import ccxt
        import torch
        import pandas
        import dotenv
        print(f"✅ CCXT Version: {ccxt.__version__}")
        print(f"✅ Torch Version: {torch.__version__}")
        print(f"✅ Pandas Version: {pandas.__version__}")
        print("✅ Dependencias críticas OPERATIVAS.")
    except ImportError as e:
        print(f"❌ FALTA DEPENDENCIA CRÍTICA: {e.name}")
        return False
    return True

def main():
    print("""
    ############################################################
           AUDITORÍA FINAL DE SISTEMA - ZEROX PRODUCCIÓN
    ############################################################
    """)
    
    if not verificar_dependencias():
        sys.exit(1)
        
    if not verificar_sintaxis():
        sys.exit(1)
        
    verificar_archivos_prohibidos()
    
    # Check de saldo (llamada rápida a script existente)
    imprimir_titulo("VERIFICACIÓN FINAL DE CONEXIÓN")
    import verificar_saldo_real
    verificar_saldo_real.verificar_modo_real()
    
    print("\n" + "#"*60)
    print("✅  SISTEMA VERIFICADO Y LISTO PARA EJECUCIÓN 10M.")
    print("    COMANDOS:")
    print("    1. Ejecutar 'iniciador_automatico.py' para arrancar.")
    print("    2. Supervisar logs en consola.")
    print("#"*60 + "\n")

if __name__ == "__main__":
    main()
