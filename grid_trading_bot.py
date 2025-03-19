#!/usr/bin/env python3
"""
Bot de Trading Automático con Grid Trading Adaptativo
"""

import time
import math
import logging
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException
import config

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("trading_bot")

class GridTradingBot:
    """
    Bot de trading que implementa la estrategia de Grid Trading Adaptativo
    para operaciones pequeñas y seguras con crecimiento diario.
    """
    
    def __init__(self):
        """Inicializa el bot de trading con la configuración predeterminada"""
        self.client = Client(
            api_key=config.TESTNET_API_KEY,
            api_secret=config.TESTNET_API_SECRET,
            testnet=True
        )
        
        # Parámetros de trading
        self.symbol = config.TRADING_SYMBOL
        self.investment_amount = config.INVESTMENT_AMOUNT
        self.take_profit_percent = config.TAKE_PROFIT_PERCENT
        self.stop_loss_percent = config.STOP_LOSS_PERCENT
        self.max_trades_per_day = config.MAX_TRADES_PER_DAY
        self.risk_percentage = config.RISK_PERCENTAGE
        
        # Parámetros de la cuadrícula
        self.grid_levels = config.GRID_LEVELS
        self.grid_spacing_percent = config.GRID_SPACING_PERCENT
        
        # Estado del bot
        self.active_orders = {}
        self.completed_trades = []
        self.daily_trades_count = 0
        self.last_grid_update = datetime.now()
        self.grid_prices = []
        
        logger.info(f"Bot inicializado para {self.symbol} con {self.grid_levels} niveles")
    
    def get_account_balance(self, asset="USDT"):
        """Obtiene el balance disponible de un activo específico"""
        try:
            account_info = self.client.get_account()
            for balance in account_info['balances']:
                if balance['asset'] == asset:
                    return float(balance['free'])
            return 0.0
        except BinanceAPIException as e:
            logger.error(f"Error al obtener balance: {e}")
            return 0.0
    
    def get_current_price(self):
        """Obtiene el precio actual del par de trading"""
        try:
            ticker = self.client.get_symbol_ticker(symbol=self.symbol)
            return float(ticker['price'])
        except BinanceAPIException as e:
            logger.error(f"Error al obtener precio: {e}")
            return None
    
    def calculate_grid_prices(self):
        """Calcula los precios de la cuadrícula basados en el precio actual y la volatilidad"""
        current_price = self.get_current_price()
        if not current_price:
            return False
        
        # Obtener datos históricos para calcular la volatilidad
        klines = self.client.get_historical_klines(
            self.symbol, Client.KLINE_INTERVAL_1HOUR, "1 day ago UTC"
        )
        
        # Calcular la volatilidad (desviación estándar de los precios)
        prices = [float(kline[4]) for kline in klines]  # Precio de cierre
        avg_price = sum(prices) / len(prices)
        variance = sum([(p - avg_price) ** 2 for p in prices]) / len(prices)
        volatility = math.sqrt(variance) / avg_price * 100  # Volatilidad en porcentaje
        
        # Ajustar el espaciado de la cuadrícula según la volatilidad
        # Más volatilidad = mayor espaciado
        adjusted_spacing = max(self.grid_spacing_percent, volatility / 10)
        
        # Calcular el rango de la cuadrícula (±1.5% por defecto, ajustado por volatilidad)
        grid_range = 1.5 * (1 + volatility / 100)
        upper_limit = current_price * (1 + grid_range / 100)
        lower_limit = current_price * (1 - grid_range / 100)
        
        # Crear la cuadrícula de precios
        self.grid_prices = []
        for i in range(self.grid_levels):
            # Distribuir los niveles uniformemente entre los límites
            level_price = lower_limit + (upper_limit - lower_limit) * i / (self.grid_levels - 1)
            self.grid_prices.append(round(level_price, 2))
        
        self.last_grid_update = datetime.now()
        logger.info(f"Cuadrícula actualizada: {self.grid_prices}")
        logger.info(f"Volatilidad: {volatility:.2f}%, Espaciado ajustado: {adjusted_spacing:.2f}%")
        return True
    
    def place_grid_orders(self):
        """Coloca órdenes de compra y venta en los niveles de la cuadrícula"""
        if not self.grid_prices:
            if not self.calculate_grid_prices():
                return False
        
        current_price = self.get_current_price()
        if not current_price:
            return False
        
        # Cancelar órdenes activas existentes
        self.cancel_all_orders()
        
        # Calcular el tamaño de la orden base
        usdt_balance = self.get_account_balance("USDT")
        order_size_usdt = min(self.investment_amount, usdt_balance * self.risk_percentage / 100)
        
        # Colocar nuevas órdenes en cada nivel de la cuadrícula
        for i, price in enumerate(self.grid_prices):
            try:
                # Ajustar el tamaño de la orden según la distancia desde el precio medio
                # Órdenes más pequeñas en los extremos
                distance_factor = 1 - abs(i - (self.grid_levels - 1) / 2) / (self.grid_levels - 1)
                adjusted_order_size = order_size_usdt * (0.5 + 0.5 * distance_factor)
                
                # Calcular la cantidad en la moneda base (BTC)
                quantity = adjusted_order_size / price
                
                # Redondear la cantidad según las reglas del mercado
                info = self.client.get_symbol_info(self.symbol)
                lot_size_filter = next(filter(lambda x: x['filterType'] == 'LOT_SIZE', info['filters']))
                step_size = float(lot_size_filter['stepSize'])
                quantity = self.round_step_size(quantity, step_size)
                
                if price < current_price:
                    # Colocar orden de compra
                    order = self.client.create_test_order(
                        symbol=self.symbol,
                        side=Client.SIDE_BUY,
                        type=Client.ORDER_TYPE_LIMIT,
                        timeInForce=Client.TIME_IN_FORCE_GTC,
                        quantity=quantity,
                        price=price
                    )
                    logger.info(f"Orden de compra colocada en {price}: {quantity} {self.symbol.replace('USDT', '')}")
                    
                    # En un entorno real, usaríamos:
                    # order = self.client.create_order(...)
                    # self.active_orders[order['orderId']] = {
                    #     'price': price,
                    #     'quantity': quantity,
                    #     'side': 'BUY',
                    #     'status': 'NEW'
                    # }
                    
                else:
                    # Colocar orden de venta
                    order = self.client.create_test_order(
                        symbol=self.symbol,
                        side=Client.SIDE_SELL,
                        type=Client.ORDER_TYPE_LIMIT,
                        timeInForce=Client.TIME_IN_FORCE_GTC,
                        quantity=quantity,
                        price=price
                    )
                    logger.info(f"Orden de venta colocada en {price}: {quantity} {self.symbol.replace('USDT', '')}")
                    
                    # En un entorno real, usaríamos:
                    # order = self.client.create_order(...)
                    # self.active_orders[order['orderId']] = {
                    #     'price': price,
                    #     'quantity': quantity,
                    #     'side': 'SELL',
                    #     'status': 'NEW'
                    # }
                
            except BinanceAPIException as e:
                logger.error(f"Error al colocar orden en nivel {price}: {e}")
        
        return True
    
    def round_step_size(self, quantity, step_size):
        """Redondea la cantidad al step_size más cercano"""
        precision = int(round(-math.log10(step_size)))
        return round(quantity - (quantity % step_size), precision)
    
    def cancel_all_orders(self):
        """Cancela todas las órdenes activas"""
        try:
            orders = self.client.get_open_orders(symbol=self.symbol)
            for order in orders:
                self.client.cancel_order(
                    symbol=self.symbol,
                    orderId=order['orderId']
                )
                logger.info(f"Orden cancelada: {order['orderId']}")
            
            self.active_orders = {}
            return True
        except BinanceAPIException as e:
            logger.error(f"Error al cancelar órdenes: {e}")
            return False
    
    def check_completed_orders(self):
        """Verifica si hay órdenes completadas y actualiza el estado"""
        try:
            # En un entorno real, verificaríamos las órdenes completadas
            # y actualizaríamos self.completed_trades y self.daily_trades_count
            
            # Simulación para testnet
            logger.info("Verificando órdenes completadas (simulación)")
            return True
        except BinanceAPIException as e:
            logger.error(f"Error al verificar órdenes completadas: {e}")
            return False
    
    def should_update_grid(self):
        """Determina si es necesario actualizar la cuadrícula"""
        # Actualizar la cuadrícula si han pasado más de 24 horas
        hours_since_update = (datetime.now() - self.last_grid_update).total_seconds() / 3600
        if hours_since_update >= 24:
            return True
        
        # Actualizar si el precio actual está fuera del rango de la cuadrícula
        if self.grid_prices:
            current_price = self.get_current_price()
            if current_price:
                min_price = min(self.grid_prices)
                max_price = max(self.grid_prices)
                if current_price < min_price * 0.98 or current_price > max_price * 1.02:
                    return True
        
        return False
    
    def reset_daily_counter(self):
        """Reinicia el contador diario de operaciones"""
        self.daily_trades_count = 0
        logger.info("Contador diario de operaciones reiniciado")
    
    def run(self):
        """Ejecuta el bucle principal del bot"""
        logger.info("Iniciando bot de trading...")
        
        try:
            # Verificar conexión
            server_time = self.client.get_server_time()
            logger.info(f"Conectado a Binance. Tiempo del servidor: {server_time}")
            
            # Configuración inicial
            if not self.calculate_grid_prices():
                logger.error("No se pudo calcular la cuadrícula inicial. Abortando.")
                return
            
            # Bucle principal
            while True:
                # Verificar si es necesario actualizar la cuadrícula
                if self.should_update_grid():
                    logger.info("Actualizando cuadrícula...")
                    self.calculate_grid_prices()
                    self.place_grid_orders()
                
                # Verificar órdenes completadas
                self.check_completed_orders()
                
                # Verificar si se ha alcanzado el límite diario de operaciones
                if self.daily_trades_count >= self.max_trades_per_day:
                    logger.info(f"Límite diario de operaciones alcanzado ({self.max_trades_per_day}). Esperando al siguiente día.")
                    # En un entorno real, esperaríamos hasta el siguiente día
                    # Por ahora, simplemente reiniciamos el contador para la demostración
                    self.reset_daily_counter()
                
                # Mostrar estado actual
                current_price = self.get_current_price()
                usdt_balance = self.get_account_balance("USDT")
                btc_balance = self.get_account_balance(self.symbol.replace("USDT", ""))
                
                logger.info(f"Precio actual: {current_price} USDT")
                logger.info(f"Balance USDT: {usdt_balance}")
                logger.info(f"Balance {self.symbol.replace('USDT', '')}: {btc_balance}")
                logger.info(f"Operaciones hoy: {self.daily_trades_count}/{self.max_trades_per_day}")
                
                # Esperar antes de la siguiente iteración
                logger.info(f"Esperando {config.CHECK_INTERVAL} segundos...")
                time.sleep(config.CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("Bot detenido manualmente.")
            self.cancel_all_orders()
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            self.cancel_all_orders()

if __name__ == "__main__":
    bot = GridTradingBot()
    bot.run()
