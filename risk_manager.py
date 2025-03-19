#!/usr/bin/env python3
"""
Módulo de gestión de riesgos para el bot de trading
"""

import logging
import json
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from binance.client import Client
from binance.exceptions import BinanceAPIException

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("risk_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("risk_manager")

class RiskManager:
    """
    Gestor de riesgos para el bot de trading que implementa múltiples
    capas de protección para garantizar operaciones seguras.
    """
    
    def __init__(self, client, config):
        """Inicializa el gestor de riesgos con la configuración proporcionada"""
        self.client = client
        self.config = config
        self.symbol = config.TRADING_SYMBOL
        
        # Parámetros de gestión de riesgos
        self.max_daily_loss_percent = 2.0  # Pérdida máxima diaria permitida (%)
        self.max_position_size_percent = 5.0  # Tamaño máximo de posición (% del capital)
        self.max_open_positions = 10  # Número máximo de posiciones abiertas
        self.market_volatility_threshold = 5.0  # Umbral de volatilidad para pausar operaciones (%)
        self.min_balance_reserve = 20.0  # Reserva mínima de balance (%)
        
        # Estado del gestor de riesgos
        self.daily_pnl = 0.0
        self.initial_daily_balance = 0.0
        self.trading_paused = False
        self.pause_reason = ""
        self.risk_metrics = {}
        
        # Historial de operaciones
        self.trades_history_file = "trades_history.json"
        self.trades_history = self._load_trades_history()
        
        # Inicializar balance diario
        self._initialize_daily_balance()
        
        logger.info("Gestor de riesgos inicializado")
    
    def _initialize_daily_balance(self):
        """Inicializa el balance diario para el seguimiento de P&L"""
        try:
            account_info = self.client.get_account()
            total_balance = 0.0
            
            # Calcular el valor total en USDT
            for balance in account_info['balances']:
                if float(balance['free']) > 0 or float(balance['locked']) > 0:
                    asset = balance['asset']
                    free_amount = float(balance['free'])
                    locked_amount = float(balance['locked'])
                    total_amount = free_amount + locked_amount
                    
                    if asset == 'USDT':
                        total_balance += total_amount
                    else:
                        # Convertir a USDT si es posible
                        try:
                            ticker = self.client.get_symbol_ticker(symbol=f"{asset}USDT")
                            price = float(ticker['price'])
                            total_balance += total_amount * price
                        except:
                            # Si no hay par con USDT, intentar con BTC y luego convertir
                            try:
                                ticker_btc = self.client.get_symbol_ticker(symbol=f"{asset}BTC")
                                price_btc = float(ticker_btc['price'])
                                ticker_btc_usdt = self.client.get_symbol_ticker(symbol="BTCUSDT")
                                price_btc_usdt = float(ticker_btc_usdt['price'])
                                total_balance += total_amount * price_btc * price_btc_usdt
                            except:
                                # Si no se puede convertir, ignorar
                                pass
            
            self.initial_daily_balance = total_balance
            logger.info(f"Balance diario inicial: {self.initial_daily_balance} USDT")
            return True
        except BinanceAPIException as e:
            logger.error(f"Error al inicializar balance diario: {e}")
            return False
    
    def _load_trades_history(self):
        """Carga el historial de operaciones desde el archivo"""
        if os.path.exists(self.trades_history_file):
            try:
                with open(self.trades_history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error al cargar historial de operaciones: {e}")
                return []
        else:
            return []
    
    def _save_trades_history(self):
        """Guarda el historial de operaciones en el archivo"""
        try:
            with open(self.trades_history_file, 'w') as f:
                json.dump(self.trades_history, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error al guardar historial de operaciones: {e}")
            return False
    
    def add_trade_to_history(self, trade_data):
        """Añade una operación al historial y actualiza el P&L diario"""
        trade_data['timestamp'] = datetime.now().isoformat()
        self.trades_history.append(trade_data)
        self._save_trades_history()
        
        # Actualizar P&L diario
        if 'pnl' in trade_data:
            self.daily_pnl += trade_data['pnl']
            logger.info(f"P&L diario actualizado: {self.daily_pnl} USDT")
    
    def calculate_position_size(self, price):
        """
        Calcula el tamaño óptimo de posición basado en la volatilidad
        y el riesgo máximo permitido
        """
        try:
            # Obtener balance disponible
            account_info = self.client.get_account()
            usdt_balance = 0.0
            for balance in account_info['balances']:
                if balance['asset'] == 'USDT':
                    usdt_balance = float(balance['free'])
                    break
            
            # Reserva mínima
            available_balance = usdt_balance * (1 - self.min_balance_reserve / 100)
            
            # Calcular volatilidad reciente
            klines = self.client.get_historical_klines(
                self.symbol, Client.KLINE_INTERVAL_1HOUR, "1 day ago UTC"
            )
            
            prices = [float(kline[4]) for kline in klines]  # Precio de cierre
            returns = [prices[i] / prices[i-1] - 1 for i in range(1, len(prices))]
            volatility = np.std(returns) * 100  # Volatilidad en porcentaje
            
            # Ajustar el tamaño de posición según la volatilidad
            # Mayor volatilidad = menor tamaño de posición
            volatility_factor = max(0.2, 1 - volatility / 20)  # Mínimo 20% del tamaño normal
            
            # Calcular tamaño máximo de posición
            max_position_size = available_balance * (self.max_position_size_percent / 100) * volatility_factor
            
            # Limitar al tamaño de inversión configurado
            position_size = min(max_position_size, self.config.INVESTMENT_AMOUNT)
            
            logger.info(f"Tamaño de posición calculado: {position_size} USDT (factor volatilidad: {volatility_factor:.2f})")
            return position_size
        except Exception as e:
            logger.error(f"Error al calcular tamaño de posición: {e}")
            return self.config.INVESTMENT_AMOUNT * 0.5  # Valor conservador por defecto
    
    def should_pause_trading(self):
        """
        Determina si el trading debe pausarse basado en condiciones de mercado
        y límites de riesgo
        """
        try:
            # Verificar pérdida diaria máxima
            if self.daily_pnl < 0 and abs(self.daily_pnl) > (self.initial_daily_balance * self.max_daily_loss_percent / 100):
                self.trading_paused = True
                self.pause_reason = f"Pérdida diaria máxima alcanzada: {abs(self.daily_pnl)} USDT"
                logger.warning(self.pause_reason)
                return True
            
            # Verificar volatilidad del mercado
            klines = self.client.get_historical_klines(
                self.symbol, Client.KLINE_INTERVAL_15MINUTE, "4 hours ago UTC"
            )
            
            prices = [float(kline[4]) for kline in klines]  # Precio de cierre
            returns = [prices[i] / prices[i-1] - 1 for i in range(1, len(prices))]
            recent_volatility = np.std(returns) * 100 * 4  # Anualizada
            
            if recent_volatility > self.market_volatility_threshold:
                self.trading_paused = True
                self.pause_reason = f"Alta volatilidad del mercado: {recent_volatility:.2f}%"
                logger.warning(self.pause_reason)
                return True
            
            # Verificar número de posiciones abiertas
            open_orders = self.client.get_open_orders(symbol=self.symbol)
            if len(open_orders) >= self.max_open_positions:
                self.trading_paused = True
                self.pause_reason = f"Número máximo de posiciones abiertas alcanzado: {len(open_orders)}"
                logger.warning(self.pause_reason)
                return True
            
            # Si llegamos aquí, no hay razón para pausar
            self.trading_paused = False
            self.pause_reason = ""
            return False
        except Exception as e:
            logger.error(f"Error al evaluar condiciones de pausa: {e}")
            return False
    
    def calculate_risk_metrics(self):
        """Calcula métricas de riesgo basadas en el historial de operaciones"""
        try:
            if not self.trades_history:
                return {}
            
            # Convertir historial a DataFrame para análisis
            df = pd.DataFrame(self.trades_history)
            
            # Asegurarse de que hay columna de PnL
            if 'pnl' not in df.columns:
                return {}
            
            # Convertir timestamp a datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Filtrar operaciones de los últimos 7 días
            week_ago = datetime.now() - timedelta(days=7)
            recent_df = df[df['timestamp'] > week_ago]
            
            if len(recent_df) == 0:
                return {}
            
            # Calcular métricas
            win_rate = len(recent_df[recent_df['pnl'] > 0]) / len(recent_df) * 100
            avg_profit = recent_df[recent_df['pnl'] > 0]['pnl'].mean() if len(recent_df[recent_df['pnl'] > 0]) > 0 else 0
            avg_loss = recent_df[recent_df['pnl'] < 0]['pnl'].mean() if len(recent_df[recent_df['pnl'] < 0]) > 0 else 0
            profit_factor = abs(recent_df[recent_df['pnl'] > 0]['pnl'].sum() / recent_df[recent_df['pnl'] < 0]['pnl'].sum()) if recent_df[recent_df['pnl'] < 0]['pnl'].sum() != 0 else float('inf')
            
            # Calcular drawdown
            cumulative = recent_df['pnl'].cumsum()
            max_dd = 0
            peak = cumulative.iloc[0]
            
            for value in cumulative:
                if value > peak:
                    peak = value
                dd = (peak - value) / peak * 100 if peak > 0 else 0
                max_dd = max(max_dd, dd)
            
            # Guardar métricas
            self.risk_metrics = {
                'win_rate': win_rate,
                'avg_profit': avg_profit,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'max_drawdown': max_dd,
                'sharpe_ratio': self._calculate_sharpe_ratio(recent_df['pnl']),
                'total_trades': len(recent_df),
                'profitable_trades': len(recent_df[recent_df['pnl'] > 0]),
                'losing_trades': len(recent_df[recent_df['pnl'] < 0])
            }
            
            logger.info(f"Métricas de riesgo calculadas: {self.risk_metrics}")
            return self.risk_metrics
        except Exception as e:
            logger.error(f"Error al calcular métricas de riesgo: {e}")
            return {}
    
    def _calculate_sharpe_ratio(self, returns, risk_free_rate=0.02/365):
        """Calcula el ratio de Sharpe para una serie de retornos"""
        if len(returns) < 2:
            return 0
        
        mean_return = returns.mean()
        std_return = returns.std()
        
        if std_return == 0:
            return 0
        
        return (mean_return - risk_free_rate) / std_return * np.sqrt(365)  # Anualizado
    
    def adjust_parameters_based_on_performance(self):
        """Ajusta los parámetros del bot basado en el rendimiento reciente"""
        if not self.risk_metrics:
            self.calculate_risk_metrics()
            
        if not self.risk_metrics:
            return False
        
        try:
            # Ajustar parámetros basados en win rate y profit factor
            win_rate = self.risk_metrics.get('win_rate', 50)
            profit_factor = self.risk_metrics.get('profit_factor', 1)
            max_drawdown = self.risk_metrics.get('max_drawdown', 0)
            
            # Ajustar tamaño de inversión
            if win_rate > 60 and profit_factor > 1.5 and max_drawdown < 10:
                # Buen rendimiento, podemos ser un poco más agresivos
                new_investment = min(self.config.INVESTMENT_AMOUNT * 1.1, 
                                    self.config.INVESTMENT_AMOUNT * 2)  # Máximo doble del original
                logger.info(f"Aumentando tamaño de inversión a {new_investment} USDT debido al buen rendimiento")
                self.config.INVESTMENT_AMOUNT = new_investment
            elif win_rate < 40 or profit_factor < 1 or max_drawdown > 20:
                # Mal rendimiento, reducir exposición
                new_investment = max(self.config.INVESTMENT_AMOUNT * 0.8, 
                                    self.config.INVESTMENT_AMOUNT * 0.5)  # Mínimo mitad del original
                logger.info(f"Reduciendo tamaño de inversión a {new_investment} USDT debido al rendimiento subóptimo")
                self.config.INVESTMENT_AMOUNT = new_investment
            
            # Ajustar take profit y stop loss
            if win_rate < 45 and self.config.TAKE_PROFIT_PERCENT > 0.7:
                # Si ganamos poco, reducir objetivo de beneficio para cerrar trades más rápido
                self.config.TAKE_PROFIT_PERCENT *= 0.9
                logger.info(f"Reduciendo take profit a {self.config.TAKE_PROFIT_PERCENT:.2f}%")
            
            if max_drawdown > 15 and self.config.STOP_LOSS_PERCENT < 0.7:
                # Si el drawdown es alto, ajustar stop loss para salir antes
                self.config.STOP_LOSS_PERCENT *= 0.9
                logger.info(f"Ajustando stop loss a {self.config.STOP_LOSS_PERCENT:.2f}%")
            
            return True
        except Exception as e:
            logger.error(f"Error al ajustar parámetros: {e}")
            return False
    
    def get_status_report(self):
        """Genera un informe de estado del gestor de riesgos"""
        if not self.risk_metrics:
            self.calculate_risk_metrics()
        
        status = {
            "trading_status": "Pausado" if self.trading_paused else "Activo",
            "pause_reason": self.pause_reason if self.trading_paused else "",
            "daily_pnl": self.daily_pnl,
            "daily_pnl_percent": (self.daily_pnl / self.initial_daily_balance * 100) if self.initial_daily_balance > 0 else 0,
            "risk_metrics": self.risk_metrics,
            "current_parameters": {
                "investment_amount": self.config.INVESTMENT_AMOUNT,
                "take_profit_percent": self.config.TAKE_PROFIT_PERCENT,
                "stop_loss_percent": self.config.STOP_LOSS_PERCENT,
                "max_trades_per_day": self.config.MAX_TRADES_PER_DAY
            }
        }
        
        return status
    
    def reset_daily_metrics(self):
        """Reinicia las métricas diarias (debe llamarse al inicio de cada día)"""
        self.daily_pnl = 0.0
        self._initialize_daily_balance()
        self.trading_paused = False
        self.pause_reason = ""
        logger.info("Métricas diarias reiniciadas")
        return True
