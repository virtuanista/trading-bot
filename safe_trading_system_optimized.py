#!/usr/bin/env python3
"""
Sistema de Trading Seguro Optimizado
"""

import time
import logging
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException
import config
from grid_trading_bot_optimized import GridTradingBotOptimized
from risk_manager import RiskManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_system_optimized.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("trading_system_optimized")

class SafeTradingSystemOptimized:
    """
    Sistema de trading seguro optimizado que integra el bot de trading con el gestor de riesgos
    para garantizar operaciones con bajo riesgo y crecimiento diario.
    """
    
    def __init__(self):
        """Inicializa el sistema de trading seguro optimizado"""
        # Inicializar cliente de Binance
        self.client = Client(
            api_key=config.TESTNET_API_KEY,
            api_secret=config.TESTNET_API_SECRET,
            testnet=True
        )
        
        # Inicializar componentes
        self.bot = GridTradingBotOptimized()
        self.risk_manager = RiskManager(self.client, config)
        
        # Estado del sistema
        self.is_running = False
        self.last_parameter_adjustment = datetime.now()
        self.last_status_report = datetime.now()
        self.market_condition = "neutral"  # neutral, bullish, bearish
        
        logger.info("Sistema de trading seguro optimizado inicializado")
    
    def analyze_market_condition(self):
        """Analiza la condición actual del mercado para ajustar la estrategia"""
        try:
            # Obtener datos históricos
            klines = self.client.get_historical_klines(
                self.bot.symbol, Client.KLINE_INTERVAL_4HOUR, "3 days ago UTC"
            )
            
            if len(klines) < 12:  # Necesitamos al menos 12 períodos de 4 horas
                return "neutral"
            
            # Calcular medias móviles
            prices = [float(kline[4]) for kline in klines]  # Precio de cierre
            ma_short = sum(prices[-6:]) / 6  # Media móvil de 24 horas (6 períodos de 4h)
            ma_long = sum(prices[-12:]) / 12  # Media móvil de 48 horas (12 períodos de 4h)
            
            # Calcular tendencia
            if ma_short > ma_long * 1.005:  # 0.5% por encima
                new_condition = "bullish"
            elif ma_short < ma_long * 0.995:  # 0.5% por debajo
                new_condition = "bearish"
            else:
                new_condition = "neutral"
            
            # Registrar cambio de condición
            if new_condition != self.market_condition:
                logger.info(f"Condición del mercado cambiada: {self.market_condition} -> {new_condition}")
                self.market_condition = new_condition
            
            return self.market_condition
            
        except Exception as e:
            logger.error(f"Error al analizar condición del mercado: {e}")
            return "neutral"
    
    def adjust_strategy_for_market_condition(self):
        """Ajusta la estrategia según la condición del mercado"""
        condition = self.analyze_market_condition()
        
        if condition == "bullish":
            # En mercado alcista, aumentar take profit y reducir stop loss
            logger.info("Ajustando estrategia para mercado alcista")
            self.bot.take_profit_percent = config.TAKE_PROFIT_PERCENT * 1.2
            self.bot.stop_loss_percent = config.STOP_LOSS_PERCENT * 0.8
            # Ajustar distribución de la cuadrícula para favorecer niveles superiores
            if self.bot.grid_prices:
                current_price = self.bot.get_current_price()
                if current_price:
                    # Recalcular cuadrícula con sesgo alcista
                    self.bot.calculate_grid_prices()
        
        elif condition == "bearish":
            # En mercado bajista, reducir take profit y aumentar stop loss
            logger.info("Ajustando estrategia para mercado bajista")
            self.bot.take_profit_percent = config.TAKE_PROFIT_PERCENT * 0.8
            self.bot.stop_loss_percent = config.STOP_LOSS_PERCENT * 1.2
            # Ajustar distribución de la cuadrícula para favorecer niveles inferiores
            if self.bot.grid_prices:
                current_price = self.bot.get_current_price()
                if current_price:
                    # Recalcular cuadrícula con sesgo bajista
                    self.bot.calculate_grid_prices()
        
        else:  # neutral
            # En mercado neutral, usar valores predeterminados
            logger.info("Ajustando estrategia para mercado neutral")
            self.bot.take_profit_percent = config.TAKE_PROFIT_PERCENT
            self.bot.stop_loss_percent = config.STOP_LOSS_PERCENT
    
    def start(self):
        """Inicia el sistema de trading seguro optimizado"""
        logger.info("Iniciando sistema de trading seguro optimizado...")
        self.is_running = True
        
        try:
            # Verificar conexión
            server_time = self.client.get_server_time()
            logger.info(f"Conectado a Binance. Tiempo del servidor: {server_time}")
            
            # Configuración inicial
            if not self.bot.calculate_grid_prices():
                logger.error("No se pudo calcular la cuadrícula inicial. Abortando.")
                return
            
            # Analizar condición inicial del mercado
            self.analyze_market_condition()
            self.adjust_strategy_for_market_condition()
            
            # Bucle principal
            while self.is_running:
                # Verificar si el trading debe pausarse por razones de riesgo
                if self.risk_manager.should_pause_trading():
                    logger.warning(f"Trading pausado: {self.risk_manager.pause_reason}")
                    time.sleep(config.CHECK_INTERVAL)
                    continue
                
                # Verificar si es necesario actualizar la cuadrícula
                if self.bot.should_update_grid():
                    logger.info("Actualizando cuadrícula...")
                    self.bot.calculate_grid_prices()
                    self.bot.place_grid_orders()
                
                # Verificar órdenes completadas
                self.bot.check_completed_orders()
                
                # Verificar si se ha alcanzado el límite diario de operaciones
                if self.bot.daily_trades_count >= self.bot.max_trades_per_day:
                    logger.info(f"Límite diario de operaciones alcanzado ({self.bot.max_trades_per_day}). Esperando al siguiente día.")
                    self.bot.reset_daily_counter()
                
                # Ajustar parámetros basados en rendimiento (cada 12 horas)
                hours_since_adjustment = (datetime.now() - self.last_parameter_adjustment).total_seconds() / 3600
                if hours_since_adjustment >= 12:
                    logger.info("Ajustando parámetros basados en rendimiento...")
                    self.risk_manager.adjust_parameters_based_on_performance()
                    self.adjust_strategy_for_market_condition()  # También ajustar según condición del mercado
                    self.last_parameter_adjustment = datetime.now()
                
                # Generar informe de estado (cada 4 horas)
                hours_since_report = (datetime.now() - self.last_status_report).total_seconds() / 3600
                if hours_since_report >= 4:
                    status_report = self.risk_manager.get_status_report()
                    logger.info(f"Informe de estado: {status_report}")
                    logger.info(f"Condición del mercado: {self.market_condition}")
                    self.last_status_report = datetime.now()
                
                # Mostrar estado actual
                current_price = self.bot.get_current_price()
                usdt_balance = self.bot.get_account_balance("USDT")
                btc_balance = self.bot.get_account_balance(self.bot.symbol.replace("USDT", ""))
                
                logger.info(f"Precio actual: {current_price} USDT")
                logger.info(f"Balance USDT: {usdt_balance}")
                logger.info(f"Balance {self.bot.symbol.replace('USDT', '')}: {btc_balance}")
                logger.info(f"Operaciones hoy: {self.bot.daily_trades_count}/{self.bot.max_trades_per_day}")
                logger.info(f"P&L diario: {self.risk_manager.daily_pnl} USDT")
                
                # Esperar antes de la siguiente iteración
                logger.info(f"Esperando {config.CHECK_INTERVAL} segundos...")
                time.sleep(config.CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("Sistema detenido manualmente.")
            self.stop()
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            self.stop()
    
    def stop(self):
        """Detiene el sistema de trading seguro optimizado"""
        logger.info("Deteniendo sistema de trading seguro optimizado...")
        self.is_running = False
        self.bot.cancel_all_orders()
        logger.info("Sistema detenido.")

if __name__ == "__main__":
    system = SafeTradingSystemOptimized()
    system.start()
