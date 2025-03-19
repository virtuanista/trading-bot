#!/usr/bin/env python3
"""
Integración del bot de trading con el gestor de riesgos
"""

import time
import logging
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException
import config
from grid_trading_bot import GridTradingBot
from risk_manager import RiskManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("trading_system")

class SafeTradingSystem:
    """
    Sistema de trading seguro que integra el bot de trading con el gestor de riesgos
    para garantizar operaciones con bajo riesgo y crecimiento diario.
    """
    
    def __init__(self):
        """Inicializa el sistema de trading seguro"""
        # Inicializar cliente de Binance
        self.client = Client(
            api_key=config.TESTNET_API_KEY,
            api_secret=config.TESTNET_API_SECRET,
            testnet=True
        )
        
        # Inicializar componentes
        self.bot = GridTradingBot()
        self.risk_manager = RiskManager(self.client, config)
        
        # Estado del sistema
        self.is_running = False
        self.last_parameter_adjustment = datetime.now()
        self.last_status_report = datetime.now()
        
        logger.info("Sistema de trading seguro inicializado")
    
    def start(self):
        """Inicia el sistema de trading seguro"""
        logger.info("Iniciando sistema de trading seguro...")
        self.is_running = True
        
        try:
            # Verificar conexión
            server_time = self.client.get_server_time()
            logger.info(f"Conectado a Binance. Tiempo del servidor: {server_time}")
            
            # Configuración inicial
            if not self.bot.calculate_grid_prices():
                logger.error("No se pudo calcular la cuadrícula inicial. Abortando.")
                return
            
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
                
                # Ajustar parámetros basados en rendimiento (cada 24 horas)
                hours_since_adjustment = (datetime.now() - self.last_parameter_adjustment).total_seconds() / 3600
                if hours_since_adjustment >= 24:
                    logger.info("Ajustando parámetros basados en rendimiento...")
                    self.risk_manager.adjust_parameters_based_on_performance()
                    self.last_parameter_adjustment = datetime.now()
                
                # Generar informe de estado (cada 6 horas)
                hours_since_report = (datetime.now() - self.last_status_report).total_seconds() / 3600
                if hours_since_report >= 6:
                    status_report = self.risk_manager.get_status_report()
                    logger.info(f"Informe de estado: {status_report}")
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
        """Detiene el sistema de trading seguro"""
        logger.info("Deteniendo sistema de trading seguro...")
        self.is_running = False
        self.bot.cancel_all_orders()
        logger.info("Sistema detenido.")

if __name__ == "__main__":
    system = SafeTradingSystem()
    system.start()
