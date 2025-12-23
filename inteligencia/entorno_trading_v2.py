import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd

class EntornoTradingBitgetV2(gym.Env):
    """
    Entorno de Trading V2 para Bitget compatible con Gymnasium.
    Soporta acciones discretas: Mantener, Comprar (Largo), Vender (Corto).
    
    MEJORAS V2:
    - Integración de 'sentiment_index' (Indice de Miedo y Codicia).
    - Normalización Híbrida: Z-Score para mercado, MinMax para sentimiento.
    """
    metadata = {'render_modes': ['human']}

    def __init__(self, df, saldo_inicial=10, comision=0.0006, tamano_ventana=50, render_mode=None):
        super(EntornoTradingBitgetV2, self).__init__()

        self.df = df.reset_index(drop=True)
        self.render_mode = render_mode
        self.tamano_ventana = tamano_ventana
        self.saldo_inicial = saldo_inicial
        self.comision = comision
        
        # Pre-cálculo de indicadores y limpieza
        self._procesar_datos()

        # Definir espacios de acción
        # Acciones: 0=Mantener, 1=Comprar/Largo, 2=Vender/Corto
        self.action_space = spaces.Discrete(3)

        # Observación: Ventana de 50 velas * (OHLCV + 4 Indicadores + 1 Sentimiento) = 10 caracteristicas
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, 
            shape=(tamano_ventana, 10), 
            dtype=np.float32
        )

        # Variables de estado
        self.paso_actual = self.tamano_ventana
        self.balance = self.saldo_inicial
        self.posicion = 0
        self.precio_entrada = 0
        self.valor_cartera_previo = self.saldo_inicial
        self.historial_retornos = []

    def _procesar_datos(self):
        """Calcula indicadores y prepara la matriz de datos"""
        # 0. Limpieza y manejo de Sentimiento
        if 'sentiment_index' not in self.df.columns:
            print("⚠️ ADVERTENCIA: 'sentiment_index' no encontrado. Usando valor neutral 50.")
            self.df['sentiment_index'] = 50.0
            
        # Rellenar NaNs en sentimiento
        self.df['sentiment_index'] = self.df['sentiment_index'].ffill().fillna(50.0)
        
        # Normalizar Sentimiento GLOBALMENTE a [0, 1]
        self.df['sentiment_norm'] = self.df['sentiment_index'] / 100.0

        # 1. RSI (14)
        delta = self.df['close'].diff()
        ganancia = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        perdida = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = ganancia / perdida
        self.df['rsi'] = 100 - (100 / (1 + rs))

        # 2. MACD (12, 26, 9)
        exp1 = self.df['close'].ewm(span=12, adjust=False).mean()
        exp2 = self.df['close'].ewm(span=26, adjust=False).mean()
        self.df['macd'] = exp1 - exp2

        # 3. Bandas de Bollinger (20, 2)
        self.df['bb_medio'] = self.df['close'].rolling(window=20).mean()
        self.df['bb_std'] = self.df['close'].rolling(window=20).std()
        self.df['bb_superior'] = self.df['bb_medio'] + (self.df['bb_std'] * 2)
        self.df['bb_inferior'] = self.df['bb_medio'] - (self.df['bb_std'] * 2)
        self.df['bb_ancho'] = (self.df['bb_superior'] - self.df['bb_inferior']) / self.df['bb_medio']

        # 4. ATR (14)
        alto_bajo = self.df['high'] - self.df['low']
        alto_cierre = np.abs(self.df['high'] - self.df['close'].shift())
        bajo_cierre = np.abs(self.df['low'] - self.df['close'].shift())
        rangos = pd.concat([alto_bajo, alto_cierre, bajo_cierre], axis=1)
        rango_verdadero = np.max(rangos, axis=1)
        self.df['atr'] = rango_verdadero.rolling(14).mean()

        # Rellenar NaNs de indicadores
        self.df.fillna(0, inplace=True)

        # Convertir a matriz numpy
        cols_caracteristicas = ['open', 'high', 'low', 'close', 'volume', 'rsi', 'macd', 'bb_ancho', 'atr', 'sentiment_norm']
        self.matriz_datos = self.df[cols_caracteristicas].values.astype(np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        self.paso_actual = self.tamano_ventana
        self.balance = self.saldo_inicial
        self.posicion = 0
        self.precio_entrada = 0
        self.valor_cartera_previo = self.saldo_inicial
        self.historial_retornos = []
        
        observacion = self._obtener_observacion()
        info = {'balance': self.balance}
        
        return observacion, info

    def _obtener_observacion(self):
        """
        Devuelve la ventana de datos normalizada.
        """
        # Obtener ventana
        ventana = self.matriz_datos[self.paso_actual - self.tamano_ventana : self.paso_actual]
        
        # Separar Mercado y Sentimiento
        caracteristicas_mercado = ventana[:, :9] 
        caracteristica_sentimiento = ventana[:, 9:] 
        
        # Normalización Z-Score para Mercado
        medias = np.mean(caracteristicas_mercado, axis=0)
        desviaciones = np.std(caracteristicas_mercado, axis=0) + 1e-8
        mercado_norm = (caracteristicas_mercado - medias) / desviaciones
        
        # Concatenar de nuevo
        obs_final = np.hstack([mercado_norm, caracteristica_sentimiento])
        
        return obs_final

    def step(self, action):
        precio_actual = self.matriz_datos[self.paso_actual, 3] # Precio de cierre
        recompensa = 0
        penalizacion_paso = -0.01

        # --- Ejecución de Órdenes ---
        if action == 1: # COMPRAR
            if self.posicion == 0:
                self.posicion = 1
                self.precio_entrada = precio_actual
                self.balance *= (1 - self.comision)
            elif self.posicion == -1: # Cerrar corto y abrir largo
                pnl = (self.precio_entrada - precio_actual) / self.precio_entrada
                self.balance *= (1 + pnl) * (1 - self.comision)
                self.posicion = 1
                self.precio_entrada = precio_actual
                self.balance *= (1 - self.comision)

        elif action == 2: # VENDER
            if self.posicion == 0:
                self.posicion = -1
                self.precio_entrada = precio_actual
                self.balance *= (1 - self.comision)
            elif self.posicion == 1: # Cerrar largo y abrir corto
                pnl = (precio_actual - self.precio_entrada) / self.precio_entrada
                self.balance *= (1 + pnl) * (1 - self.comision)
                self.posicion = -1
                self.precio_entrada = precio_actual
                self.balance *= (1 - self.comision)

        # --- Valoración ---
        valor_cartera = self.balance
        if self.posicion == 1:
            pnl_no_realizado = (precio_actual - self.precio_entrada) / self.precio_entrada
            valor_cartera = self.balance * (1 + pnl_no_realizado)
        elif self.posicion == -1:
            pnl_no_realizado = (self.precio_entrada - precio_actual) / self.precio_entrada
            valor_cartera = self.balance * (1 + pnl_no_realizado)

        # --- Recompensa Sortino ---
        retorno_paso = (valor_cartera - self.valor_cartera_previo) / self.valor_cartera_previo
        self.valor_cartera_previo = valor_cartera
        self.historial_retornos.append(retorno_paso)
        
        recompensa = retorno_paso * 100
        if retorno_paso < 0:
            recompensa *= 2.5 
        recompensa += penalizacion_paso

        # --- Terminación ---
        terminado = False
        truncado = False
        
        if valor_cartera < (self.saldo_inicial * 0.5): # Ruina
            terminado = True
            recompensa = -100
        
        self.paso_actual += 1
        if self.paso_actual >= len(self.df) - 1:
            truncado = True

        info = {
            'retorno_paso': retorno_paso,
            'valor_cartera': valor_cartera,
            'posicion': self.posicion
        }

        return self._obtener_observacion(), recompensa, terminado, truncado, info

    def render(self):
        print(f"Paso: {self.paso_actual}, Balance: {self.balance:.2f}, Pos: {self.posicion}")
