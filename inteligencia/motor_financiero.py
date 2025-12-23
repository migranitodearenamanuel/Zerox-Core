import pandas as pd
import numpy as np
import datetime
import os

# =============================================================================
# 💰 MOTOR FINANCIERO - ALGORITMO DE LOS 10 MILLONES
# =============================================================================
# ARCHIVO: motor_financiero.py
# PROPÓSITO: Calcular cuánto riesgo debemos tomar para alcanzar la meta.
# Se basa en el Interés Compuesto: pequeñas ganancias diarias suman millones.
# =============================================================================

class Gestor10M:
    def __init__(self):
        self.capital_inicial = 30.0 # Empezamos con 30 euros
        self.objetivo_final = 10000000.0 # Meta: 10 Millones
        self.dias_totales = 1460 # 4 años
        
        # Fecha de inicio fija para mantener la curva constante
        self.fecha_inicio = datetime.date(2023, 1, 1) 
        self.archivo_progreso = os.path.join(os.path.dirname(__file__), "progreso_10m.csv")
        
        # Calcular tasa de crecimiento diaria necesaria (Fórmula del Interés Compuesto)
        # VF = VI * (1 + r)^t  =>  r = (VF / VI)^(1/t) - 1
        self.tasa_diaria = (self.objetivo_final / self.capital_inicial) ** (1 / self.dias_totales) - 1
        # Esto nos da aprox un 0.87% diario necesario.
        # Si ganamos 1% al día, llegamos antes.

    def calcular_objetivo_hoy(self):
        """Calcula cuánto dinero deberíamos tener HOY para ir en camino correcto."""
        dias_transcurridos = (datetime.date.today() - self.fecha_inicio).days
        if dias_transcurridos < 0: dias_transcurridos = 0
        
        objetivo_hoy = self.capital_inicial * ((1 + self.tasa_diaria) ** dias_transcurridos)
        return objetivo_hoy, dias_transcurridos

    def calcular_agresividad(self, capital_actual):
        """
        Determina el nivel de riesgo (Apalancamiento) necesario.
        Si vamos perdiendo, arriesgamos más (Antigravedad).
        Si vamos ganando, protegemos el capital.
        """
        objetivo_hoy, dias = self.calcular_objetivo_hoy()
        
        # Guardar en el historial
        self.registrar_progreso(capital_actual, objetivo_hoy)
        
        info = {
            "dia": dias,
            "objetivo_teorico": round(objetivo_hoy, 2),
            "capital_real": round(capital_actual, 2),
            "desviacion": round(capital_actual - objetivo_hoy, 2)
        }

        if capital_actual < objetivo_hoy:
            # MODO RECUPERACIÓN: Estamos perdiendo la carrera contra el interés compuesto.
            # Necesitamos más riesgo para volver a la curva exponencial.
            info["modo"] = "RECUPERACIÓN (ANTIGRAVITY)"
            info["apalancamiento_recomendado"] = 20 # Arriesgado
            info["mensaje"] = "⚠️ POR DEBAJO DEL OBJETIVO. AUMENTAR POTENCIA."
        else:
            # MODO CONSERVADOR: Vamos ganando. Proteger el capital es prioridad.
            info["modo"] = "CONSERVADOR (ESCUDO)"
            info["apalancamiento_recomendado"] = 5 # Seguro
            info["mensaje"] = "✅ POR ENCIMA DEL OBJETIVO. REDUCIR RIESGO."

        return info

    def registrar_progreso(self, real, objetivo):
        """Guarda el estado diario en un archivo CSV (Excel)."""
        existe = os.path.exists(self.archivo_progreso)
        with open(self.archivo_progreso, "a") as f:
            if not existe:
                f.write("fecha,dia_num,saldo_real,saldo_objetivo\n")
            
            hoy = datetime.date.today()
            dias = (hoy - self.fecha_inicio).days
            f.write(f"{hoy},{dias},{real:.2f},{objetivo:.2f}\n")

# Prueba rápida (Solo se ejecuta si corres este archivo directamente)
if __name__ == "__main__":
    gestor = Gestor10M()
    # Simular que tenemos 40 euros (vamos bien)
    print(gestor.calcular_agresividad(40))
    # Simular que tenemos 20 euros (vamos mal)
    print(gestor.calcular_agresividad(20))
