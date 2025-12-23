import numpy as np
import pandas as pd


def ema(serie: pd.Series, periodo: int) -> pd.Series:
    return serie.ewm(span=int(periodo), adjust=False).mean()


def rsi(serie: pd.Series, periodo: int = 14) -> pd.Series:
    periodo = int(periodo)
    delta = serie.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.rolling(window=periodo, min_periods=periodo).mean()
    avg_loss = loss.rolling(window=periodo, min_periods=periodo).mean()
    rs = avg_gain / (avg_loss.replace(0, np.nan))
    out = 100 - (100 / (1 + rs))
    return out.fillna(50.0)


def macd(serie: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    fast = int(fast)
    slow = int(slow)
    signal = int(signal)
    ema_fast = ema(serie, fast)
    ema_slow = ema(serie, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def atr(df: pd.DataFrame, periodo: int = 14) -> pd.Series:
    periodo = int(periodo)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=periodo, min_periods=periodo).mean().fillna(0.0)


def adx(df: pd.DataFrame, periodo: int = 14) -> pd.Series:
    """
    ADX (Average Directional Index) simplificado.
    Devuelve serie 0..100 (aprox). Si no hay datos suficientes, devuelve 0.
    """
    periodo = int(periodo)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr = atr(df, periodo=1)
    tr_n = tr.rolling(window=periodo, min_periods=periodo).sum()

    plus_di = 100 * (pd.Series(plus_dm, index=df.index).rolling(window=periodo, min_periods=periodo).sum() / tr_n.replace(0, np.nan))
    minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(window=periodo, min_periods=periodo).sum() / tr_n.replace(0, np.nan))
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    adx_series = dx.rolling(window=periodo, min_periods=periodo).mean()
    return adx_series.fillna(0.0)


def vwap(df: pd.DataFrame) -> pd.Series:
    """
    VWAP basado en datos de velas (cálculo acumulativo sobre la ventana recibida).
    """
    typical = (df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)) / 3.0
    vol = df["volume"].astype(float).replace(0, np.nan)
    cum_pv = (typical * vol).cumsum()
    cum_v = vol.cumsum()
    return (cum_pv / cum_v).ffill().fillna(typical)


def obv(df: pd.DataFrame) -> pd.Series:
    close = df["close"].astype(float)
    vol = df["volume"].astype(float)
    direction = np.sign(close.diff().fillna(0.0))
    return (direction * vol).cumsum().fillna(0.0)


def volumen_ratio(df: pd.DataFrame, periodo: int = 20) -> float:
    """
    Ratio de volumen actual vs media móvil simple del volumen.
    """
    if df is None or len(df) < 3 or "volume" not in df:
        return 0.0
    periodo = int(periodo)
    vol = df["volume"].astype(float)
    media = vol.rolling(window=periodo, min_periods=max(3, periodo // 2)).mean()
    v_actual = float(vol.iloc[-1])
    v_media = float(media.iloc[-1]) if not np.isnan(media.iloc[-1]) else 0.0
    if v_media <= 0:
        return 0.0
    return v_actual / v_media

