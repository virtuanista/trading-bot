#!/usr/bin/env python3
"""
Bot de Trading Automático con Grid Trading Adaptativo (Versión Optimizada)
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
        logging.FileHandler("trading_bot_optimized.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("trading_bot_optimized")

class GridTradingBotOptimized:
    """
    Bot de trading optimizado que implementa la estrategia de Grid Trading Adaptativo
    para operaciones pequeñas y seguras con crecimiento diario.
    """
    
    def __init__(self):
        """Inicializa el bot de trading con la configuración optimizada"""
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
        
        # Parámetros de gestión de riesgos optimizados
        self.trailing_stop_percent = config.TRAILING_STOP_PERCENT
        
        # Estado del bot
        self.active_orders = {}
        self.completed_trades = []
        self.daily_trades_count = 0
        self.last_grid_update = datetime.now()
        self.grid_prices = []
        self.trailing_stops = {}  # Para almacenar los trailing stops de las posiciones abiertas
        
        logger.info(f"Bot optimizado inicializado para {self.symbol} con {self.grid_levels} niveles")
        logger.info(f"Parámetros optimizados: Espaciado={self.grid_spacing_percent}%, TP={self.take_profit_percent}%, SL={self.stop_loss_percent}%")
    
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
        # Más volatilidad = mayor espaciado, pero con un límite inferior optimizado
        adjusted_spacing = max(self.grid_spacing_percent, volatility / 15)  # Optimizado: divisor aumentado para espaciado más pequeño
        
        # Calcular el rango de la cuadrícula (optimizado: rango más estrecho para mayor precisión)
        grid_range = 1.2 * (1 + volatility / 120)  # Optimizado: factores ajustados para rango más preciso
        upper_limit = current_price * (1 + grid_range / 100)
        lower_limit = current_price * (1 - grid_range / 100)
        
        # Crear la cuadrícula de precios con distribución no lineal (optimizado)
        # Más niveles cerca del precio actual para mayor precisión
        self.grid_prices = []
        for i in range(self.grid_levels):
            # Distribución no lineal para concentrar niveles cerca del precio actual
            power = 3  # Factor de no linealidad
            normalized_position = ((i / (self.grid_levels - 1)) * 2 - 1) ** power  # Entre -1 y 1, con concentración en el centro
            level_position = (normalized_position + 1) / 2  # Entre 0 y 1
            
            level_price = lower_limit + (upper_limit - lower_limit) * level_position
            self.grid_prices.append(round(level_price, 2))
        
        # Ordenar los precios para asegurar que estén en orden ascendente
        self.grid_prices.sort()
        
        self.last_grid_update = datetime.now()
        logger.info(f"Cuadrícula optimizada actualizada: {self.grid_prices}")
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
                # Órdenes más pequeñas en los extremos (optimizado: distribución más agresiva)
                distance_factor = 1 - abs(i - (self.grid_levels - 1) / 2) / (self.grid_levels - 1)
                adjusted_order_size = order_size_usdt * (0.4 + 0.6 * distance_factor)  # Optimizado: factor base reducido
                
                # Calcular la cantidad en la moneda base (BTC)
                quantity = adjusted_order_size / price
                
                # Redondear la cantidad según las reglas del mercado
                info = self.client.get_symbol_info(self.symbol)
                lot_size_filter = next(filter(lambda x: x['filterType'] == 'LOT_SIZE', info['filters']))
                step_size = float(lot_size_filter['stepSize'])
                quantity = self.round_step_size(quantity, step_size)
                
                # Calcular niveles de take profit y stop loss dinámicos
                take_profit = price * (1 + self.take_profit_percent / 100)
                stop_loss = price * (1 - self.stop_loss_percent / 100)
                
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
                    logger.info(f"Take profit: {take_profit}, Stop loss: {stop_loss}")
                    
                    # En un entorno real, usaríamos:
                    # order = self.client.create_order(...)
                    # self.active_orders[order['orderId']] = {
                    #     'price': price,
                    #     'quantity': quantity,
                    #     'side': 'BUY',
                    #     'status': 'NEW',
                    #     'take_profit': take_profit,
                    #     'stop_loss': stop_loss,
                    #     'trailing_stop_activated': False,
                    #     'trailing_stop_price': None
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
                    logger.info(f"Take profit: {price * (1 - self.take_profit_percent / 100)}, Stop loss: {price * (1 + self.stop_loss_percent / 100)}")
                    
                    # En un entorno real, usaríamos:
                    # order = self.client.create_order(...)
                    # self.active_orders[order['orderId']] = {
                    #     'price': price,
                    #     'quantity': quantity,
                    #     'side': 'SELL',
                    #     'status': 'NEW',
                    #     'take_profit': price * (1 - self.take_profit_percent / 100),
                    #     'stop_loss': price * (1 + self.stop_loss_percent / 100),
                    #     'trailing_stop_activated': False,
                    #     'trailing_stop_price': None
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
    
    def update_trailing_stops(self, current_price):
        """Actualiza los trailing stops para las posiciones abiertas"""
        for order_id, order_data in self.active_orders.items():
            if order_data['status'] == 'FILLED':
                # Solo para órdenes ya ejecutadas
                if order_data['side'] == 'BUY':
                    # Para posiciones largas
                    if not order_data['trailing_stop_activated']:
                        # Activar trailing stop cuando el precio alcanza un cierto nivel
                        activation_price = order_data['price'] * (1 + self.take_profit_percent / 200)  # 50% del take profit
                        if current_price >= activation_price:
                            order_data['trailing_stop_activated'] = True
                            order_data['trailing_stop_price'] = current_price * (1 - self.trailing_stop_percent / 100)
                            logger.info(f"Trailing stop activado para orden {order_id} en {order_data['trailing_stop_price']}")
                    else:
                        # Actualizar trailing stop si el precio sube
                        new_stop_price = current_price * (1 - self.trailing_stop_percent / 100)
                        if new_stop_price > order_data['trailing_stop_price']:
                            order_data['trailing_stop_price'] = new_stop_price
                            logger.info(f"Trailing stop actualizado para orden {order_id} en {new_stop_price}")
                
                elif order_data['side'] == 'SELL':
                    # Para posiciones cortas
                    if not order_data['trailing_stop_activated']:
                        activation_price = order_data['price'] * (1 - self.take_profit_percent / 200)
                        if current_price <= activation_price:
                            order_data['trailing_stop_activated'] = True
                            order_data['trailing_stop_price'] = current_price * (1 + self.trailing_stop_percent / 100)
                            logger.info(f"Trailing stop activado para orden {order_id} en {order_data['trailing_stop_price']}")
                    else:
                        new_stop_price = current_price * (1 + self.trailing_stop_percent / 100)
                        if new_stop_price < order_data['trailing_stop_price']:
                            order_data['trailing_stop_price'] = new_stop_price
                            logger.info(f"Trailing stop actualizado para orden {order_id} en {new_stop_price}")
    
    def check_trailing_stops(self, current_price):
        """Verifica si algún trailing stop ha sido alcanzado"""
        orders_to_close = []
        
        for order_id, order_data in self.active_orders.items():
            if order_data['status'] == 'FILLED' and order_data['trailing_stop_activated']:
                if order_data['side'] == 'BUY' and current_price <= order_data['trailing_stop_price']:
                    # Cerrar posición larga
                    logger.info(f"Trailing stop alcanzado para orden {order_id} en {current_price}")
                    orders_to_close.append((order_id, order_data))
                
                elif order_data['side'] == 'SELL' and current_price >= order_data['trailing_stop_price']:
                    # Cerrar posición corta
                    logger.info(f"Trailing stop alcanzado para orden {order_id} en {current_price}")
                    orders_to_close.append((order_id, order_data))
        
        # Cerrar las posiciones que alcanzaron el trailing stop
        for order_id, order_data in orders_to_close:
            self.close_position(order_id, order_data, current_price, 'TRAILING_STOP')
    
    def close_position(self, order_id, order_data, current_price, reason):
        """Cierra una posición abierta"""
        try:
            side = Client.SIDE_SELL if order_data['side'] == 'BUY' else Client.SIDE_BUY
            
            # En un entorno real, usaríamos:
            # close_order = self.client.create_order(
            #     symbol=self.symbol,
            #     side=side,
            #     type=Client.ORDER_TYPE_MARKET,
            #     quantity=order_data['quantity']
            # )
            
            # Calcular PnL
            if order_data['side'] == 'BUY':
                pnl = (current_price - order_data['price']) * order_data['quantity']
            else:
                pnl = (order_data['price'] - current_price) * order_data['quantity']
            
            # Registrar operación completada
            trade_data = {
                'order_id': order_id,
                'entry_price': order_data['price'],
                'exit_price': current_price,
                'quantity': order_data['quantity'],
                'side': order_data['side'],
                'pnl': pnl,
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            }
            
            self.completed_trades.append(trade_data)
            self.daily_trades_count += 1
            
            # Eliminar de órdenes activas
            del self.active_orders[order_id]
            
            logger.info(f"Posición cerrada: {trade_data}")
            return True
            
        except Exception as e:
            logger.error(f"Error al cerrar posición: {e}")
            return False
    
    def check_completed_orders(self):
        """Verifica si hay órdenes completadas y actualiza el estado"""
        try:
            # En un entorno real, verificaríamos las órdenes completadas
            # y actualizaríamos self.completed_trades y self.daily_trades_count
            
            # Simulación para testnet
            logger.info("Verificando órdenes completadas (simulación)")
            
            # Verificar take profit y stop loss para órdenes simuladas
            current_price = self.get_current_price()
            if current_price:
                # Actualizar trailing stops
                self.update_trailing_stops(current_price)
                
                # Verificar si algún trailing stop ha sido alcanzado
                self.check_trailing_stops(current_price)
                
                # Verificar take profit y stop loss
                for order_id, order_data in list(self.active_orders.items()):
                    if order_data['status'] == 'FILLED':
                        if order_data['side'] == 'BUY':
                            # Verificar take profit para posiciones largas
                            if current_price >= order_data['take_profit']:
                                self.close_position(order_id, order_data, current_price, 'TAKE_PROFIT')
                            # Verificar stop loss para posiciones largas
                            elif current_price <= order_data['stop_loss']:
                                self.close_position(order_id, order_data, current_price, 'STOP_LOSS')
                        
                        elif order_data['side'] == 'SELL':
                            # Verificar take profit para posiciones cortas
                            if current_price <= order_data['take_profit']:
                                self.close_position(order_id, order_data, current_price, 'TAKE_PROFIT')
                            # Verificar stop loss para posiciones cortas
                            elif current_price >= order_data['stop_loss']:
                                self.close_position(order_id, order_data, current_price, 'STOP_LOSS')
            
            return True
        except Exception as e:
            logger.error(f"Error al verificar órdenes completadas: {e}")
            return False
    
    def should_update_grid(self):
        """Determina si es necesario actualizar la cuadrícula"""
        # Actualizar la cuadrícula si han pasado más de 12 horas (optimizado: más frecuente)
        hours_since_update = (datetime.now() - self.last_grid_update).total_seconds() / 3600
        if hours_since_update >= 12:
            return True
        
        # Actualizar si el precio actual está fuera del rango de la cuadrícula
        if self.grid_prices:
            current_price = self.get_current_price()
            if current_price:
                min_price = min(self.grid_prices)
                max_price = max(self.grid_prices)
                # Optimizado: umbral más sensible para actualización
                if current_price < min_price * 0.99 or current_price > max_price * 1.01:
                    return True
        
        return False
    
    def reset_daily_counter(self):
        """Reinicia el contador diario de operaciones"""
        self.daily_trades_count = 0
        logger.info("Contador diario de operaciones reiniciado")
    
    def run(self):
        """Ejecuta el bucle principal del bot"""
        logger.info("Iniciando bot de trading optimizado...")
        
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
    bot = GridTradingBotOptimized()
    bot.run()
