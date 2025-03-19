#!/usr/bin/env python3
"""
Script para probar la conexión con la API de Binance testnet
"""

import sys
from binance.client import Client
from binance.exceptions import BinanceAPIException
import config

def test_connection():
    """Prueba la conexión con la API de Binance testnet y muestra información básica de la cuenta"""
    print("Probando conexión con Binance Testnet...")
    
    try:
        # Inicializar el cliente de Binance con las claves API de testnet
        client = Client(
            api_key=config.TESTNET_API_KEY,
            api_secret=config.TESTNET_API_SECRET,
            testnet=True  # Importante: usar el entorno de testnet
        )
        
        # Verificar la conexión obteniendo información del servidor
        server_time = client.get_server_time()
        print(f"Conexión exitosa. Tiempo del servidor: {server_time}")
        
        # Obtener información de la cuenta
        account_info = client.get_account()
        print("\nInformación de la cuenta:")
        print(f"Estado de la cuenta: {account_info['accountType']}")
        print(f"Puede operar: {account_info['canTrade']}")
        print(f"Puede depositar: {account_info['canDeposit']}")
        print(f"Puede retirar: {account_info['canWithdraw']}")
        
        # Mostrar balances de activos
        print("\nBalances de activos:")
        balances = [balance for balance in account_info['balances'] 
                   if float(balance['free']) > 0 or float(balance['locked']) > 0]
        
        for balance in balances:
            print(f"Activo: {balance['asset']}, Libre: {balance['free']}, Bloqueado: {balance['locked']}")
        
        # Obtener precios actuales
        prices = client.get_all_tickers()
        print(f"\nPrecios actuales (mostrando primeros 5 de {len(prices)}):")
        for price in prices[:5]:
            print(f"{price['symbol']}: {price['price']}")
            
        return True
        
    except BinanceAPIException as e:
        print(f"Error de API de Binance: {e}")
        return False
    except Exception as e:
        print(f"Error inesperado: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
