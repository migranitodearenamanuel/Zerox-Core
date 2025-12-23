import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd

class BitgetTradingEnv(gym.Env):
    """
    Entorno de Trading personalizado para Bitget compatible con Gymnasium.
    Soporta acciones discretas: Hold, Buy (Long), Sell (Short).
    Recompensa: Sortino Ratio modificado (penalización por volatilidad negativa).
    """
    metadata = {'render_modes': ['human']}

    def __init__(self, df, initial_balance=10, commission=0.0006, window_size=50, render_mode=None):
        super(BitgetTradingEnv, self).__init__()

        self.df = df.reset_index(drop=True)
        self.render_mode = render_mode
        self.window_size = window_size
        self.initial_balance = initial_balance
        self.commission = commission
        
        # Pre-cálculo de indicadores técnicos para velocidad (Vectorizado)
        self._calculate_indicators()

        # Definir espacios de acción y observación
        # Acciones: 0=Hold, 1=Buy/Long, 2=Sell/Short
        self.action_space = spaces.Discrete(3)

        # Observación: Ventana de 50 velas * (OHLCV + 4 Indicadores) = 9 features
        # Normalizaremos los valores, por lo que usamos -inf a inf
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, 
            shape=(window_size, 9), 
            dtype=np.float32
        )

        # Variables de estado
        self.current_step = self.window_size
        self.balance = self.initial_balance
        self.position = 0 # 0: Flat, 1: Long, -1: Short
        self.entry_price = 0
        self.total_reward = 0
        self.returns_history = [] # Para cálculo de Sortino
        self.history = []

    def _calculate_indicators(self):
        """Calcula indicadores técnicos usando Pandas (fallback si no hay TA-Lib)"""
        # 1. RSI (14)
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        self.df['rsi'] = 100 - (100 / (1 + rs))

        # 2. MACD (12, 26, 9)
        exp1 = self.df['close'].ewm(span=12, adjust=False).mean()
        exp2 = self.df['close'].ewm(span=26, adjust=False).mean()
        self.df['macd'] = exp1 - exp2
        # self.df['signal'] = self.df['macd'].ewm(span=9, adjust=False).mean() # Opcional

        # 3. Bollinger Bands (20, 2)
        self.df['bb_middle'] = self.df['close'].rolling(window=20).mean()
        self.df['bb_std'] = self.df['close'].rolling(window=20).std()
        self.df['bb_upper'] = self.df['bb_middle'] + (self.df['bb_std'] * 2)
        self.df['bb_lower'] = self.df['bb_middle'] - (self.df['bb_std'] * 2)
        # Usamos el ancho de banda o posición relativa como feature
        self.df['bb_width'] = (self.df['bb_upper'] - self.df['bb_lower']) / self.df['bb_middle']

        # 4. ATR (14) - Aproximación simple con Pandas
        high_low = self.df['high'] - self.df['low']
        high_close = np.abs(self.df['high'] - self.df['close'].shift())
        low_close = np.abs(self.df['low'] - self.df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        self.df['atr'] = true_range.rolling(14).mean()

        # Rellenar NaNs iniciales
        self.df.fillna(0, inplace=True)

        # Convertir a numpy para acceso rápido en _get_observation
        self.data_matrix = self.df[['open', 'high', 'low', 'close', 'volume', 'rsi', 'macd', 'bb_width', 'atr']].values.astype(np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        self.current_step = self.window_size
        self.balance = self.initial_balance
        self.position = 0
        self.entry_price = 0
        self.total_reward = 0
        self.returns_history = []
        self.history = []
        
        observation = self._get_observation()
        info = {'balance': self.balance}
        
        return observation, info

    def _get_observation(self):
        """Devuelve la ventana de datos normalizada"""
        # Obtener ventana
        window = self.data_matrix[self.current_step - self.window_size : self.current_step]
        
        # Normalización Z-Score local (robusta para precios)
        # Normalizamos cada columna independientemente basada en la media/std de la ventana
        means = np.mean(window, axis=0)
        stds = np.std(window, axis=0) + 1e-8 # Evitar división por cero
        normalized_window = (window - means) / stds
        
        return normalized_window

    def step(self, action):
        current_price = self.data_matrix[self.current_step, 3] # Close price
        prev_balance = self.balance
        reward = 0
        step_penalty = -0.01 # Penalización por inactividad/tiempo

        # Ejecutar Acción
        # 0: Hold, 1: Buy, 2: Sell
        
        if action == 1: # BUY (Long)
            if self.position == 0: # Entrar Long
                self.position = 1
                self.entry_price = current_price
                self.balance *= (1 - self.commission) # Comisión
            elif self.position == -1: # Cerrar Short y Entrar Long (Flip)
                # Cerrar Short
                pnl = (self.entry_price - current_price) / self.entry_price
                self.balance *= (1 + pnl) * (1 - self.commission)
                # Entrar Long
                self.position = 1
                self.entry_price = current_price
                self.balance *= (1 - self.commission)
            # Si ya es Long (1), Hold implícito

        elif action == 2: # SELL (Short)
            if self.position == 0: # Entrar Short
                self.position = -1
                self.entry_price = current_price
                self.balance *= (1 - self.commission)
            elif self.position == 1: # Cerrar Long y Entrar Short (Flip)
                # Cerrar Long
                pnl = (current_price - self.entry_price) / self.entry_price
                self.balance *= (1 + pnl) * (1 - self.commission)
                # Entrar Short
                self.position = -1
                self.entry_price = current_price
                self.balance *= (1 - self.commission)
            # Si ya es Short (-1), Hold implícito

        elif action == 0: # HOLD
            # Si estamos dentro, calculamos PnL no realizado para feedback continuo?
            # Para PPO es mejor rewards continuos.
            pass

        # Calcular Valor del Portafolio Actual (Mark-to-Market)
        portfolio_value = self.balance
        if self.position == 1:
            unrealized_pnl = (current_price - self.entry_price) / self.entry_price
            portfolio_value = self.balance * (1 + unrealized_pnl)
        elif self.position == -1:
            unrealized_pnl = (self.entry_price - current_price) / self.entry_price
            portfolio_value = self.balance * (1 + unrealized_pnl)

        # --- Cálculo de Recompensa (Sortino-like) ---
        # Calculamos el retorno porcentual de este paso
        # Necesitamos el valor del portafolio del paso anterior para el retorno
        # Simplificación: Usamos el cambio en portfolio_value
        
        # Guardamos valor previo en variable de clase si quisiéramos exactitud, 
        # pero aquí usaremos una aproximación basada en PnL del paso.
        
        # Retorno logarítmico del paso
        # (Asumimos que prev_portfolio_value se trackea, lo añadiremos)
        if not hasattr(self, 'prev_portfolio_value'):
            self.prev_portfolio_value = self.initial_balance
            
        step_return = (portfolio_value - self.prev_portfolio_value) / self.prev_portfolio_value
        self.prev_portfolio_value = portfolio_value
        
        self.returns_history.append(step_return)
        
        # Recompensa Base: Retorno
        reward = step_return * 100 # Escalar para estabilidad numérica (ej. 1% -> 1.0)
        
        # Penalización por Volatilidad Negativa (Sortino Proxy)
        if step_return < 0:
            reward *= 2.5 # Penaliza x2.5 las pérdidas (Aversión al riesgo)
            
        # Penalización por paso (Time decay)
        reward += step_penalty

        # --- Gestión de Riesgo y Terminación ---
        terminated = False
        truncated = False
        
        # 1. Ruina (Drawdown > 50%)
        if portfolio_value < (self.initial_balance * 0.5):
            terminated = True
            reward = -100 # Castigo masivo por quemar la cuenta
        
        # 2. Fin del Dataset
        self.current_step += 1
        if self.current_step >= len(self.df) - 1:
            truncated = True

        # Info para debug
        info = {
            'step_return': step_return,
            'portfolio_value': portfolio_value,
            'position': self.position
        }

        return self._get_observation(), reward, terminated, truncated, info

    def render(self):
        # Visualización simple en consola
        print(f"Step: {self.current_step}, Balance: {self.balance:.2f}, Position: {self.position}")
