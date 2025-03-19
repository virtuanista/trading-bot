#!/usr/bin/env python3
"""
Script de prueba para el sistema de trading seguro optimizado
"""

import logging
import time
import sys
import os
from datetime import datetime, timedelta
from binance.client import Client
from binance.exceptions import BinanceAPIException
import config
from safe_trading_system_optimized import SafeTradingSystemOptimized

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_results_optimized.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_script_optimized")

class OptimizedTradingSystemTester:
    """
    Clase para probar el sistema de trading seguro optimizado en un entorno controlado
    """
    
    def __init__(self):
        """Inicializa el probador del sistema de trading optimizado"""
        self.client = Client(
            api_key=config.TESTNET_API_KEY,
            api_secret=config.TESTNET_API_SECRET,
            testnet=True
        )
        self.system = None
        self.test_duration = 900  # Duración de la prueba en segundos (15 minutos)
        self.check_interval = 60  # Intervalo para verificar estado (1 minuto)
        
        logger.info("Probador del sistema de trading optimizado inicializado")
    
    def verify_account_status(self):
        """Verifica el estado de la cuenta antes de las pruebas"""
        try:
            account_info = self.client.get_account()
            
            # Verificar si la cuenta puede operar
            if not account_info['canTrade']:
                logger.error("La cuenta no tiene permisos para operar. Abortando pruebas.")
                return False
            
            # Verificar balances
            balances = {}
            for balance in account_info['balances']:
                if float(balance['free']) > 0 or float(balance['locked']) > 0:
                    balances[balance['asset']] = {
                        'free': float(balance['free']),
                        'locked': float(balance['locked'])
                    }
            
            # Verificar que hay USDT suficiente para las pruebas
            if 'USDT' not in balances or balances['USDT']['free'] < 100:
                logger.warning("Balance de USDT bajo para pruebas óptimas.")
            
            logger.info(f"Cuenta verificada. Balances disponibles: {balances}")
            return True
        except BinanceAPIException as e:
            logger.error(f"Error al verificar cuenta: {e}")
            return False
    
    def run_controlled_test(self):
        """Ejecuta una prueba controlada del sistema de trading optimizado"""
        logger.info(f"Iniciando prueba controlada de {self.test_duration} segundos...")
        
        if not self.verify_account_status():
            return False
        
        try:
            # Crear y configurar el sistema
            self.system = SafeTradingSystemOptimized()
            
            # Modificar parámetros para pruebas
            # Reducir intervalos para acelerar las pruebas
            config.CHECK_INTERVAL = 30  # 30 segundos entre iteraciones
            
            # Iniciar el sistema en un hilo separado
            import threading
            system_thread = threading.Thread(target=self.system.start)
            system_thread.daemon = True
            system_thread.start()
            
            logger.info("Sistema de trading optimizado iniciado en modo de prueba")
            
            # Monitorear el sistema durante la duración de la prueba
            start_time = datetime.now()
            end_time = start_time + timedelta(seconds=self.test_duration)
            
            while datetime.now() < end_time:
                # Verificar estado del sistema
                if not system_thread.is_alive():
                    logger.error("El hilo del sistema de trading se ha detenido inesperadamente")
                    return False
                
                # Registrar estado actual
                current_price = self.system.bot.get_current_price()
                usdt_balance = self.system.bot.get_account_balance("USDT")
                btc_balance = self.system.bot.get_account_balance(self.system.bot.symbol.replace("USDT", ""))
                
                logger.info(f"Estado de prueba - Tiempo restante: {(end_time - datetime.now()).seconds} segundos")
                logger.info(f"Precio actual: {current_price} USDT")
                logger.info(f"Balance USDT: {usdt_balance}")
                logger.info(f"Balance {self.system.bot.symbol.replace('USDT', '')}: {btc_balance}")
                logger.info(f"Condición del mercado: {self.system.market_condition}")
                
                # Esperar antes de la siguiente verificación
                time.sleep(self.check_interval)
            
            # Detener el sistema al finalizar la prueba
            logger.info("Prueba completada. Deteniendo sistema...")
            self.system.stop()
            system_thread.join(timeout=30)
            
            logger.info("Prueba controlada finalizada exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error durante la prueba: {e}")
            if self.system:
                self.system.stop()
            return False
    
    def verify_test_results(self):
        """Verifica los resultados de la prueba"""
        logger.info("Verificando resultados de la prueba...")
        
        try:
            # Verificar logs generados
            log_files = ["test_results_optimized.log", "trading_system_optimized.log", "trading_bot_optimized.log", "risk_manager.log"]
            
            for log_file in log_files:
                if os.path.exists(log_file):
                    file_size = os.path.getsize(log_file)
                    logger.info(f"Archivo de log {log_file} generado: {file_size} bytes")
                else:
                    logger.warning(f"Archivo de log {log_file} no encontrado")
            
            # Verificar órdenes creadas durante la prueba
            try:
                all_orders = self.client.get_all_orders(symbol=config.TRADING_SYMBOL)
                recent_orders = [order for order in all_orders if int(order['time']) > (time.time() - self.test_duration) * 1000]
                
                logger.info(f"Órdenes creadas durante la prueba: {len(recent_orders)}")
                for order in recent_orders:
                    logger.info(f"Orden: {order['orderId']}, Tipo: {order['type']}, Lado: {order['side']}, Estado: {order['status']}")
                
            except BinanceAPIException as e:
                logger.error(f"Error al verificar órdenes: {e}")
            
            # Verificar si el historial de operaciones se ha guardado
            if os.path.exists("trades_history.json"):
                import json
                with open("trades_history.json", "r") as f:
                    trades_history = json.load(f)
                logger.info(f"Historial de operaciones guardado: {len(trades_history)} operaciones")
            
            logger.info("Verificación de resultados completada")
            return True
        except Exception as e:
            logger.error(f"Error al verificar resultados: {e}")
            return False
    
    def compare_with_original_version(self):
        """Compara el rendimiento con la versión original del bot"""
        logger.info("Comparando rendimiento con la versión original...")
        
        try:
            # Verificar si existen logs de ambas versiones
            original_log = "trading_bot.log"
            optimized_log = "trading_bot_optimized.log"
            
            if not os.path.exists(original_log) or not os.path.exists(optimized_log):
                logger.warning("No se pueden encontrar logs de ambas versiones para comparar")
                return False
            
            # Analizar logs para extraer métricas clave
            original_metrics = self._extract_metrics_from_log(original_log)
            optimized_metrics = self._extract_metrics_from_log(optimized_log)
            
            # Comparar métricas
            logger.info("=== Comparación de Rendimiento ===")
            logger.info(f"Versión Original: {original_metrics}")
            logger.info(f"Versión Optimizada: {optimized_metrics}")
            
            # Calcular mejoras
            improvements = {}
            for key in optimized_metrics:
                if key in original_metrics and original_metrics[key] != 0:
                    change = ((optimized_metrics[key] - original_metrics[key]) / original_metrics[key]) * 100
                    improvements[key] = f"{change:.2f}%"
            
            logger.info(f"Mejoras: {improvements}")
            
            return True
        except Exception as e:
            logger.error(f"Error al comparar rendimiento: {e}")
            return False
    
    def _extract_metrics_from_log(self, log_file):
        """Extrae métricas clave de un archivo de log"""
        metrics = {
            "operations_count": 0,
            "successful_operations": 0,
            "response_time": 0,
            "grid_levels": 0
        }
        
        try:
            with open(log_file, 'r') as f:
                content = f.readlines()
            
            for line in content:
                if "Operaciones hoy:" in line:
                    parts = line.split("Operaciones hoy:")[1].strip().split("/")
                    if len(parts) > 0:
                        metrics["operations_count"] = int(parts[0])
                
                if "Posición cerrada:" in line and "pnl" in line and "pnl': " in line:
                    metrics["successful_operations"] += 1
                
                if "Cuadrícula" in line and "niveles" in line:
                    parts = line.split("con")[1].split("niveles")[0].strip()
                    try:
                        metrics["grid_levels"] = int(parts)
                    except:
                        pass
            
            return metrics
        except Exception as e:
            logger.error(f"Error al extraer métricas de {log_file}: {e}")
            return metrics

def main():
    """Función principal para ejecutar las pruebas"""
    logger.info("=== INICIANDO PRUEBAS DEL SISTEMA DE TRADING OPTIMIZADO ===")
    
    tester = OptimizedTradingSystemTester()
    
    # Ejecutar prueba controlada
    test_success = tester.run_controlled_test()
    
    # Verificar resultados
    if test_success:
        results_verified = tester.verify_test_results()
        
        # Comparar con versión original
        comparison_done = tester.compare_with_original_version()
        
        if results_verified:
            logger.info("=== PRUEBAS COMPLETADAS EXITOSAMENTE ===")
            return 0
        else:
            logger.warning("=== PRUEBAS COMPLETADAS CON ADVERTENCIAS EN LA VERIFICACIÓN ===")
            return 1
    else:
        logger.error("=== PRUEBAS FALLIDAS ===")
        return 2

if __name__ == "__main__":
    sys.exit(main())
