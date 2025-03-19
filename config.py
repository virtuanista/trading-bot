import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()

# Configuración de la API de Binance (Testnet)
TESTNET_API_KEY = ""
TESTNET_API_SECRET = ""

# Configuración del bot
TRADING_SYMBOL = "BTCUSDT"  # Par de trading predeterminado
INVESTMENT_AMOUNT = 100.0    # Cantidad en USDT para invertir por operación
TAKE_PROFIT_PERCENT = 0.7    # Porcentaje de beneficio objetivo (0.7%) - OPTIMIZADO: Reducido para cerrar operaciones más rápido
STOP_LOSS_PERCENT = 0.3      # Porcentaje de pérdida máxima permitida (0.3%) - OPTIMIZADO: Más estricto para reducir drawdown
MAX_TRADES_PER_DAY = 8       # Número máximo de operaciones por día - OPTIMIZADO: Aumentado para permitir más operaciones
RISK_PERCENTAGE = 0.8        # Porcentaje del capital total a arriesgar por operación - OPTIMIZADO: Reducido para mayor seguridad

# Configuración de la estrategia
STRATEGY_TYPE = "grid_trading"  # Tipo de estrategia: grid_trading, dca, etc.
GRID_LEVELS = 7                 # Número de niveles para grid trading - OPTIMIZADO: Aumentado para más oportunidades
GRID_SPACING_PERCENT = 0.3      # Espaciado entre niveles en porcentaje - OPTIMIZADO: Reducido para aumentar frecuencia de operaciones

# Configuración de intervalos
CHECK_INTERVAL = 180  # Intervalo para verificar precios (en segundos) - OPTIMIZADO: Reducido para mayor reactividad

# Configuración adicional de gestión de riesgos (OPTIMIZADO)
MAX_DAILY_LOSS_PERCENT = 1.5    # Pérdida máxima diaria permitida (%)
MIN_BALANCE_RESERVE = 30.0      # Reserva mínima de balance (%) - Aumentado para mayor seguridad
VOLATILITY_PAUSE_THRESHOLD = 4.0 # Umbral de volatilidad para pausar operaciones (%)
TRAILING_STOP_PERCENT = 0.2     # Porcentaje para stop loss dinámico (trailing stop)
